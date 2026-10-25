// Parse every hand-written YAML with Bun, the way tests/run_local_tests.sh does.
// Usage: bun check_yaml.ts <file> [<file> ...]
for (const f of process.argv.slice(2)) {
  try {
    Bun.YAML.parse(await Bun.file(f).text());
  } catch (e) {
    console.error(`FAIL ${f}: ${e}`);
    process.exit(1);
  }
}
console.log(`parsed ${process.argv.length - 2} files`);
