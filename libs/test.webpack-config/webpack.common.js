const path = require('path');

module.exports = {
  entry: './src/index.ts',
  resolve: {
    // Add `.ts` and `.tsx` as a resolvable extension.
    extensions: [".ts", ".tsx", ".js"]
  }
};