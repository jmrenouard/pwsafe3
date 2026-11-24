# How to Build and Run the pwsafe3 Container

Use this procedure to build the Docker image, convert a TSV file, and verify output safety.

## Prerequisites

- Confirm Docker is installed on the host.
- Confirm your TSV file uses `GROUP:` headers and five tab-delimited fields per row.

NOTE: Review all CLI options and column rules in [CLI, TSV Schema, and Dockerfile Reference](../03-reference/cli-tsv-schema-and-dockerfile.md).

## Procedure

### Build the Container Image

1. Run `docker build` from the repository root:

```bash
docker build -t psafe3 .
```

### Convert a TSV File Safely

WARNING: Remove plaintext secrets from shell arguments before shared execution. Pass the master password through `PWSAFE3_PASSWORD` so process lists stay clean.

1. Set the vault password environment variable in your shell:

```bash
read -rs -p "Vault password: " PWSAFE3_PASSWORD && export PWSAFE3_PASSWORD && echo
```

2. Run `drun.sh` with your TSV file and a new `.psafe3` filename:

```bash
sh drun.sh input.tsv output.psafe3
```

3. Remove the temporary password variable from your shell environment:

```bash
unset PWSAFE3_PASSWORD
```

## Validation

Confirm the generated `.psafe3` file exists and check its size:

```bash
ls -lh output.psafe3
```

Run the repository verification tests:

```bash
python3 -m unittest discover -s tests -p "test_*.py" -v
```

## Rollback

If conversion fails or you generate a wrong vault, delete the output file cleanly:

```bash
rm -f output.psafe3
```

CAUTION: Delete source TSV files only after you verify access to your saved `.psafe3` vault.

Read container and vault design notes in [Vault Format and Container Security](../04-explanation/vault-format-and-container-security.md).
