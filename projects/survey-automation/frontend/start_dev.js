// Wrapper to start Next.js dev server from the correct working directory
process.chdir(__dirname);

// Preview tool sets PORT env var. Pass it to Next.js via --port
const port = process.env.PORT || '3000';
process.argv.push('dev', '--port', port);

require('next/dist/bin/next');
