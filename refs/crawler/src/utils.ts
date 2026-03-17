import { createHash } from 'node:crypto';
import { parseDomain, ParseResultType } from 'parse-domain';
import { ElementHandle } from 'playwright';

/**
 * Hash an object using SHA256
 */
export function hashObjectSha256(object: any): string {
  return createHash('sha256').update(JSON.stringify(object)).digest('hex');
}

/**
 * Extend the URL class to returns the effective domain
 */
export class URLPlus extends URL {
  get effectiveDomain(): string {
    const parsed = parseDomain(this.hostname);

    if (parsed.type === ParseResultType.Listed) {
      return parsed.domain + '.' + parsed.topLevelDomains.join('.');
    }

    return this.hostname;
  }
}

/**
 * Check if an element is visible, using Playwright API
 */
export async function isElementVisible(_source: any, elementHandle: ElementHandle): Promise<boolean> {
  return elementHandle.isVisible();
}

/**
 * Sleep for a given number of milliseconds
 */
export function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => { setTimeout(resolve, ms); });
}
