/* Compatibility entry point for the former machine-specific browser script.
 * This runs Node VM behavioral checks, NOT a browser or visual/layout test.
 * Actual browser and mobile checks are recorded separately through CUA.
 */
'use strict';

console.error(
  '[Telegis] Node VM checks only - this compatibility command does NOT launch a browser or verify screenshots/layout.'
);
require('./frontend_contract.cjs');
