import process from 'node:process';
import assert from 'node:assert/strict';
import { promises as fs } from 'node:fs';
import path from 'node:path';
import os from 'node:os';
import { execFileSync } from 'node:child_process';
import yargs from 'yargs';
import { hideBin } from 'yargs/helpers';

import { chromium } from 'playwright-extra';
import StealthPlugin from 'puppeteer-extra-plugin-stealth';
import mnemonist from 'mnemonist';
import { BrowserContext, Locator, Page, errors as PlaywrightErrors } from 'playwright';
import { xdgCache } from 'xdg-basedir';
import { rimraf } from 'rimraf';

import { StepSpec, JobSpec } from './types.js';
import { URLPlus, hashObjectSha256, isElementVisible, sleep } from './utils.js';
import {
  findNextSteps, markInterestingElements, getFormInformation, initFunction, patchNonFormFields,
} from './page-functions.js';
import { estimateReward } from './reward.js';

/**
 * Locate the element that match the given attributes
 */
async function locateOriginElement(page: Page, step: StepSpec): Promise<Locator | null> {
  const tagName = step.origin?.tagName || 'invalid';

  // Match by ID
  const id = step.origin?.id;

  if (id) {
    const locator = page.locator(`${tagName}[id="${id}"]`);
    if ((await locator.count()) > 0) return locator.first();
  }

  // Match by text content
  const text = step.origin?.textContent.trim();

  if (text !== '') {
    for (const element of await page.locator(tagName).all()) {
      const elemText = (await element.textContent() || '').trim();
      if (text === elemText) return element;
    }
  }

  return null;
}

class PageStateError extends Error {
  constructor(message: string) {
    super(message);
    this.name = this.constructor.name;
  }
}

async function waitForLoading(page: Page, timeout: number = 30000) {
  const tstart = performance.now();

  // Wait for networkidle but still continue if timeout
  try {
    await page.waitForLoadState('networkidle', { timeout });
  } catch (e) {
    if (!(e instanceof PlaywrightErrors.TimeoutError)) throw e;
  }

  const nextTimeout = Math.max(timeout - (performance.now() - tstart), 1);
  // At minimum, wait for DOMContentLoaded event -- should return immediately if already there
  await page.waitForLoadState('domcontentloaded', { timeout: nextTimeout });
}

async function doSteps(page: Page, steps: StepSpec[]): Promise<(string | null)[]> {
  const history: (string | null)[] = [];
  let hasNavigated = false;

  const navigationHandler = () => { hasNavigated = true; };
  page.on('domcontentloaded', navigationHandler);
  let beforeUrl = steps[0].action[1] + '/...'; // Initialize with a dummy URL of the same domain

  for (const [index, step] of steps.entries()) {
    hasNavigated = false;
    const [command, ...args] = step.action;
    let actionFunc = async () => {};

    switch (command) {
      case 'goto': {
        actionFunc = async () => {
          await page.goto(args[0], { referer: step.origin?.location, waitUntil: 'commit' });
        };
        break;
      }
      case 'click': {
        const element = await locateOriginElement(page, step);
        if (element === null) throw new PageStateError('Cannot find specified element');

        actionFunc = async () => {
          try {
            await element.click();
          } catch (e) {
            if (e instanceof PlaywrightErrors.TimeoutError) {
              await element.evaluate((elem) => (elem as HTMLElement).click());
            } else {
              throw e;
            }
          }
        };

        break;
      }
      default:
        assert.fail(`Invalid action ${command}`);
    }

    if (index + 1 === steps.length) {
      // Before the last step, mark elements generated in previous steps
      await page.evaluate(markInterestingElements);
    }

    await actionFunc();

    // Wait for possible navigation
    await page.waitForTimeout(1000);
    await waitForLoading(page);

    const afterUrl = page.url();

    // hasNavigated should have been set but just in case...
    if (beforeUrl !== afterUrl) hasNavigated = true;

    if (hasNavigated) {
      console.log('Navigated to:', afterUrl);

      const beforeUrlParsed = new URLPlus(beforeUrl);
      const afterUrlParsed = new URLPlus(afterUrl);

      if (index > 0 && beforeUrlParsed.effectiveDomain !== afterUrlParsed.effectiveDomain) {
        throw new PageStateError('Navigated to a different domain');
      }

      // Check navigation loop
      history.flatMap((s) => (s ? [new URLPlus(s)] : [])).forEach((historyUrl) => {
        if (afterUrlParsed.host === historyUrl.host
            && afterUrlParsed.pathname === historyUrl.pathname) {
          throw new PageStateError('Navigated to a previously visited URL');
        }
      });
    }

    beforeUrl = afterUrl;
    history.push(hasNavigated ? afterUrl : null);
  }

  page.off('domcontentloaded', navigationHandler);

  console.log('Successfully recovered page state. URL:', page.url());

  return history;
}

async function checkForms(page: Page, outDir: string) {
  let forms = await page.locator('form:not([data-flag-visited])').all();

  for (const [idx, form] of forms.entries()) {
    await Promise.all([
      form.screenshot({ path: path.join(outDir, `form-${idx}.png`) }).catch(() => null),
      form
        .evaluate(getFormInformation)
        .then((info) => fs.writeFile(path.join(outDir, `form-${idx}.json`), JSON.stringify(info, null, 2))),
    ]);

    console.log(`Web form #${idx} saved`);
  }

  await page.evaluate(patchNonFormFields);
  forms = await page.getByTestId('patched-form').all();

  for (const [idx, form] of forms.entries()) {
    await Promise.all([
      form.screenshot({ path: path.join(outDir, `form-p${idx}.png`) }).catch(() => null),
      form
        .evaluate(getFormInformation)
        .then((info) => fs.writeFile(path.join(outDir, `form-p${idx}.json`), JSON.stringify(info, null, 2))),
    ]);

    console.log(`Web form #p${idx} saved`);
  }
}

/**
 * Build a new step by appending the given next step to the given steps, while rejecting invalid next step
 */
function buildSteps(steps: StepSpec[], nextStep: StepSpec): StepSpec[] | null {
  if (nextStep.action[0] === 'goto') {
    let originalUrl: URLPlus;
    let nextUrl: URLPlus;

    try {
      originalUrl = new URLPlus(steps[0].action[1]);
      nextUrl = new URLPlus(nextStep.action[1]);
    } catch (e) {
      if (e instanceof TypeError) {
        console.log('Failed to parse URL:', (e as any).input);
      }

      return null;
    }

    // Do not allow cross-domain navigation
    if (originalUrl.effectiveDomain !== nextUrl.effectiveDomain) return null;

    // Avoid navigating to the same page
    if (originalUrl.pathname === nextUrl.pathname) return null;

    return [nextStep];
  }

  return [...steps, nextStep];
}

async function downloadExtensions(cacheDir: string) {
  const extensionUrls = [
    // eslint-disable-next-line max-len
    'https://github.com/OhMyGuus/I-Still-Dont-Care-About-Cookies/releases/download/v1.1.1/istilldontcareaboutcookies-1.1.1.crx',
    'https://www.eff.org/files/privacy_badger-chrome.crx',
  ];
  const returnPaths = [];

  for (const url of extensionUrls) {
    const extractPath = path.join(cacheDir, 'ext-' + btoa(url).replaceAll('/', '@'));
    const markerPath = path.join(extractPath, '.flag');
    returnPaths.push(extractPath);

    if (await fs.stat(markerPath).then(() => false).catch(() => true)) {
      console.log('Downloading extension:', url);

      const resource = await fetch(url);
      const data = await resource.arrayBuffer();

      const downloadPath = path.join(cacheDir, 'ext.crx');
      await fs.writeFile(downloadPath, Buffer.from(data));

      await fs.mkdir(extractPath, { recursive: true });
      execFileSync('bsdtar', ['-xf', downloadPath, '-C', extractPath]);
      await fs.writeFile(markerPath, '');
    }
  }

  return returnPaths;
}

async function doJob(job: JobSpec, page: Page, outDir: string): Promise<StepSpec[] | null> {
  await page.context().setOffline(false);

  // Step 1: Navigation / Repeat steps
  let navigationHistory: (string | null)[] = [];

  try {
    console.log('Navigating...');
    navigationHistory = await doSteps(page, job.steps);
  } catch (e) {
    if (e instanceof Error) {
      console.error('Failed to recover page state:', e.message);
      return null;
    }

    throw e;
  }

  await page.context().setOffline(true);

  // Step 2: Dump job information for later inspection
  try {
    console.log('Saving job information...');

    const [pageHTML, pageTitle, calledSpecialAPIs, screenshot] = await Promise.all([
      page.content(),
      page.title(),
      page.evaluate(() => (window as any).calledSpecialAPIs),
      page.screenshot({ fullPage: true }),
    ]);

    await Promise.all([
      fs.writeFile(path.join(outDir, 'page.html'), pageHTML),
      fs.writeFile(path.join(outDir, 'page.png'), screenshot),
      fs.writeFile(
        path.join(outDir, 'job.json'),
        JSON.stringify({ pageTitle, ...job, navigationHistory, calledSpecialAPIs }, null, 2),
      ),
    ]);
  } catch (e) {
    if (e instanceof Error) {
      console.error('Failed to save job information:', e.message);
      return null;
    }

    throw e;
  }

  // Step 3: Search the webpage for forms
  try {
    console.log('Checking forms...');
    await checkForms(page, outDir);
  } catch (e) {
    if (e instanceof Error) {
      console.error('Failed to check forms:', e.message);
      return null;
    }

    throw e;
  }

  // Step 4: Find possible next steps
  let nextStepChoices: StepSpec[] = [];

  try {
    nextStepChoices = await page.evaluate(findNextSteps);
  } catch (e) {
    if (e instanceof Error) {
      console.log('Failed to find next steps:', e.message);
      return null;
    }

    throw e;
  }

  await Promise.all(
    nextStepChoices.map(async (step) => {
      step.reward = step.reward = await estimateReward(step);
    }),
  );

  await fs.writeFile(
    path.join(outDir, 'next-steps.json'),
    JSON.stringify(nextStepChoices, null, 2),
  );

  return nextStepChoices;
}

async function initBrowserContext(cacheDir: string): Promise<BrowserContext> {
  // Setup extensions
  const extensionPaths = await downloadExtensions(cacheDir);

  // Initialize the browser
  const userDataDir = path.join(cacheDir, `user-data-${process.pid}`);
  await rimraf(userDataDir);
  process.on('exit', () => rimraf.sync(userDataDir));
  const browserContext = await chromium.launchPersistentContext(userDataDir, {
    args: [
      '--disable-extensions-except=' + extensionPaths.join(','),
      '--load-extension=' + extensionPaths.join(','),
    ],
    chromiumSandbox: os.userInfo().uid !== 0,
    // eslint-disable-next-line max-len
    userAgent: 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.6099.28 Safari/537.36',
    locale: 'en-US',
    timezoneId: 'America/Los_Angeles',
    serviceWorkers: 'block',
    geolocation: { latitude: 38.581667, longitude: -121.494444 },
    permissions: [
      'geolocation',
      'camera', 'microphone',
      'ambient-light-sensor', 'accelerometer', 'gyroscope', 'magnetometer',
    ],
  });
  browserContext.setDefaultTimeout(10000);

  await Promise.all([
    browserContext.addInitScript(initFunction),
    browserContext.exposeFunction('hashObjectSha256', hashObjectSha256),
    browserContext.exposeBinding('isElementVisible', isElementVisible, { handle: true }),
  ]);

  return browserContext;
}

function parseArguments(): any {
  const argv = yargs(hideBin(process.argv))
    .command('$0 <outDir> <landingURLs...>', 'Web form crawler', (_yargs) => {
      _yargs
        .positional('outDir', {
          describe: 'Output directory',
          type: 'string',
          demandOption: true,
        })
        .positional('landingURLs', {
          describe: 'Landing URLs',
          type: 'string',
          array: true,
          default: [],
        });
    })
    .option('maxJobCount', {
      describe: 'Maximum job count',
      type: 'number',
      default: 100,
    })
    .option('priorityDecayFactor', {
      describe: 'Priority decay factor',
      type: 'number',
      default: 0.90,
    })
    .option('priorityRandomizationFactor', {
      describe: 'Priority randomization factor',
      type: 'number',
      default: 0.05,
    })
    .option('minJobTime', {
      describe: 'Minimum job time (in milliseconds)',
      type: 'number',
      default: 6000, // 6 seconds
    })
    .help('help')
    .parse();

  return argv;
}

await (async () => {
  const programName = 'web-form-crawler';

  const cacheDir = path.join(xdgCache || os.tmpdir(), programName);

  const {
    outDir, landingURLs, maxJobCount, priorityDecayFactor, priorityRandomizationFactor, minJobTime,
  } = parseArguments();

  const jobQueue = new mnemonist.Heap<JobSpec>((j1, j2) => Math.sign(j2.priority - j1.priority));

  landingURLs.forEach((url: string) => jobQueue.push({
    priority: 1000,
    parents: [],
    steps: [{ action: ['goto', url], reward: NaN }],
  }));

  // Stealth plugin - not sure if it actually helps but why not
  const stealth = StealthPlugin();
  // Workaround: https://github.com/berstend/puppeteer-extra/issues/858
  stealth.enabledEvasions.delete('user-agent-override');
  chromium.use(stealth);

  let jobCount = 0;
  await fs.mkdir(cacheDir, { recursive: true });
  let browserContext = await initBrowserContext(cacheDir);
  await fs.mkdir(outDir);

  // Main loop
  while (jobCount < maxJobCount && jobQueue.size > 0) {
    const job = jobQueue.pop()!;
    const jobHash = hashObjectSha256(job.steps.map((s) => s.action));
    const jobOutDir = path.join(outDir, jobHash);
    const startTime = performance.now();

    try {
      await fs.mkdir(jobOutDir);
    } catch (e) {
      if ((e as any).code === 'EEXIST') {
        console.log('Skipping job because it has been tried before');
        continue;
      }

      throw e;
    }

    let page: Page;

    try {
      browserContext.pages().map((p) => p.close());
      page = await browserContext.newPage();
    } catch (e) {
      console.error('Failed to setup new page:', e instanceof Error ? e.message : e);

      console.log('Restarting browser...');
      await browserContext.close().catch(() => null);
      browserContext = await initBrowserContext(cacheDir);

      page = await browserContext.newPage();
    }

    console.log('Current job:', job);
    console.log(`Job ${jobHash} started`);

    // The main function -- no catch block because ignorable errors should have been handled in it
    const nextStepChoices = await doJob(job, page, jobOutDir);

    jobCount += 1;
    let newJobCount = 0;

    nextStepChoices?.forEach((step) => {
      const newSteps = buildSteps(job.steps, step);

      if (step.reward >= 0 && newSteps !== null) {
        const priority = (step.reward + priorityRandomizationFactor * Math.random())
                          * (priorityDecayFactor ** (job.parents.length + 1));

        jobQueue.push({
          priority,
          parents: [...job.parents, jobHash],
          steps: newSteps,
        });

        newJobCount += 1;
      }
    });

    console.log(`Job queue size: ${jobQueue.size} (${newJobCount} new)`);

    // Throttle the crawler
    const elapsed = performance.now() - startTime;
    if (elapsed < minJobTime) await sleep(minJobTime - elapsed);
  }

  await browserContext.close();
})();
