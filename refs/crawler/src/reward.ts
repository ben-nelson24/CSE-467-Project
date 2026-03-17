import { pipeline, cos_sim } from '@xenova/transformers';
import { StepSpec } from './types.js';

const SEED_PHRASES = `
account profile
application form
apply for a license
apply for an account
apply online
apply now
appointment
book a demo
business account
buy now
chat with us
change my address
check status of request
checkout
click to open account
click here to continue
client login
complaint form
contact center
contact sales
contact us
continue
continue with email
continue with phone number
create an account
create free account
customer service
data request form
donate
do not sell my personal data
download for free
download now
english
enter the site
enquiry form
enroll
enroll in online banking
fee payment
feedback
file a claim
file a report online
forgot id
forgot password
free trial
get a quote
get started
get this deal
give now
individual account
inquiry
instant trial
join for free
join now
join us
login
log in
logon
log on
make a gift now
make a payment
manage booking
managing my account
my account
my profile
next step
new account
new customer
open an account
opt-out here
order now
post a review
preferences
redeem a gift card
register
register a credit card
register for an account
register now
report fraud
request a demo
request records
reset password
retrieve a quote
schedule an appointment
see plans and pricing
settings
sign in
sign on
sign on to mobile banking
sign up
sitemap
submit a tip
submit feedback
submit your application
subscribe
subscribe now
subscribe today
support center
take a product tour
try for free
use phone or email
`.trim().split('\n');

/**
 * Estimate the reward of clicking an element
 */
// eslint-disable-next-line import/prefer-default-export
export const estimateReward = await (async () => {
  const pipe = await pipeline('feature-extraction', 'Xenova/all-MiniLM-L6-v2');
  const seedEmbeddings = await pipe(SEED_PHRASES, { pooling: 'mean', normalize: true });

  return async (step: StepSpec): Promise<number> => {
    let text = step?.origin?.text;
    let maxSimilarity = -1.0;

    if (!text && step.action[0] === 'goto') {
      const parsedUrl = new URL(step.action[1]);
      text = parsedUrl.pathname + parsedUrl.search;
    }

    if (text) {
      const embedding = await pipe(text, { pooling: 'mean', normalize: true });

      for (let i = 0; i < SEED_PHRASES.length; i += 1) {
        const similarity = cos_sim(seedEmbeddings[i].data, embedding.data);

        if (similarity > maxSimilarity) maxSimilarity = similarity;
      }
    }

    return maxSimilarity;
  };
})();
