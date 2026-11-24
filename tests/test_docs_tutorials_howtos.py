"""Executable tests for pwsafe3 Dockerfile, Perl converter, TSV fixture, and Diataxis docs."""

from __future__ import annotations

import os
import pathlib
import re
import shutil
import subprocess
import tempfile
import unittest
from urllib.parse import unquote

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
DOCS_DIR = REPO_ROOT / "docs"
REQUIRED_QUADRANTS = ("01-tutorials", "02-how-to-guides", "03-reference", "04-explanation")

FENCE_RE = re.compile(r"^\s*(`{3,}|~{3,})")
LINK_RE = re.compile(r"!?\[[^\]]*\]\(([^)\n]+)\)")
HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$")
ASCII_BOX_RE = re.compile(r"[┌┐└┘├┤┬┴┼═║╔╗╚╝]|^\s*\+[-+]+\+\s*$", re.M)
MERMAID_TYPES = ("graph ", "flowchart ", "sequenceDiagram", "classDiagram", "stateDiagram", "erDiagram")


def _posix_bin(cmd: str) -> str | None:
    """Return executable path on POSIX hosts so Windows runs avoid WSL wrapper quirks cleanly."""
    if os.name != "posix":
        return None
    return shutil.which(cmd)


def _github_anchor_slug(heading_text: str) -> str:
    cleaned = re.sub(r"`([^`]+)`", r"\1", heading_text.strip().lower())
    out: list[str] = []
    for ch in cleaned:
        if ch.isalnum() or ch == "_":
            out.append(ch)
        elif ch in (" ", "-"):
            out.append("-")
    return "".join(out)


def _split_fenced_blocks(text: str) -> tuple[list[tuple[int, str]], list[tuple[int, str, str]], bool]:
    non_code: list[tuple[int, str]] = []
    blocks: list[tuple[int, str, str]] = []
    in_fence = False
    fence_char = ""
    fence_len = 0
    fence_lang = ""
    fence_start = 0
    buf: list[str] = []

    for lineno, line in enumerate(text.splitlines(), 1):
        stripped = line.lstrip()
        m = FENCE_RE.match(line)
        if not in_fence:
            if m:
                marker = m.group(1)
                in_fence = True
                fence_char = marker[0]
                fence_len = len(marker)
                fence_lang = stripped[fence_len:].strip().split()[0].lower() if stripped[fence_len:].strip() else ""
                fence_start = lineno
                buf = []
                continue
            non_code.append((lineno, line))
        else:
            if stripped.startswith(fence_char * fence_len) and stripped[fence_len:].strip() == "":
                blocks.append((fence_start, fence_lang, "\n".join(buf)))
                in_fence = False
                buf = []
            else:
                buf.append(line)

    return non_code, blocks, in_fence


class TestDockerfilePerlAndTsv(unittest.TestCase):
    """Validate Dockerfile rules, drun.sh syntax, input.tsv fixture, and Perl converter."""

    def test_dockerfile_syntax_copy_targets_and_drun_quoting(self) -> None:
        """Verify Dockerfile base pinning, existing COPY targets, non-root USER, and drun.sh."""
        df = (REPO_ROOT / "Dockerfile").read_text(encoding="utf-8")
        from_match = re.search(r"(?m)^FROM\s+(\S+)", df)
        self.assertIsNotNone(from_match)
        assert from_match is not None
        self.assertFalse(from_match.group(1).endswith(":latest"), "Dockerfile base tag must be pinned")

        user_match = re.search(r"(?m)^USER\s+(\S+)", df)
        self.assertIsNotNone(user_match)
        assert user_match is not None
        self.assertNotIn(user_match.group(1), ("root", "0"))

        copy_matches = re.findall(r"(?m)^COPY\s+(?:--\S+\s+)*(\S+)\s+(\S+)", df)
        self.assertTrue(copy_matches, "Dockerfile must copy convert.pl")
        for src, dst in copy_matches:
            self.assertTrue((REPO_ROOT / src).is_file(), f"Missing COPY source: {src}")
            self.assertFalse(dst.startswith("/data/"), "Script inside /data would be shadowed by bind mount")

        self.assertIn('"/usr/local/bin/convert.pl"', df)

        drun = (REPO_ROOT / "drun.sh").read_text(encoding="utf-8")
        self.assertIn('"$(pwd):/data"', drun)
        self.assertIn('"$@"', drun)

        bash_bin = _posix_bin("bash")
        if bash_bin:
            chk = subprocess.run([bash_bin, "-n", str(REPO_ROOT / "drun.sh")], capture_output=True, text=True)
            self.assertEqual(chk.returncode, 0, chk.stderr)

    def test_sample_tsv_fixture_and_python_schema(self) -> None:
        """Deterministically validate input.tsv GROUP sections and 5-column TSV entries."""
        raw_lines = (REPO_ROOT / "input.tsv").read_text(encoding="utf-8").splitlines()
        current_group = ""
        records: list[tuple[str, list[str]]] = []
        for idx, raw in enumerate(raw_lines, 1):
            line = raw.strip()
            if not line:
                continue
            if line.startswith("GROUP:"):
                current_group = line.removeprefix("GROUP:").strip()
                self.assertTrue(current_group, f"Empty GROUP header at line {idx}")
                continue
            fields = line.split("\t")
            self.assertEqual(len(fields), 5, f"Line {idx} must have 5 tab-separated fields")
            self.assertTrue(all(f.strip() for f in fields), f"Blank column on line {idx}")
            records.append((current_group, fields))

        self.assertEqual(len(records), 4)
        self.assertEqual([g for g, _ in records], ["APP_TESTING", "APP_TESTING", "APP_PROD", "APP_PROD"])

    def test_convert_pl_perl_syntax_and_stub_execution(self) -> None:
        """Run perl -c syntax check and mocked Crypt::PWSafe3 conversion on POSIX hosts with perl."""
        pl_src = (REPO_ROOT / "convert.pl").read_text(encoding="utf-8")
        self.assertIn("use strict;", pl_src)
        self.assertIn("use warnings;", pl_src)
        self.assertIn("use Crypt::PWSafe3;", pl_src)
        self.assertIn("Access Type:", pl_src)
        self.assertLess(pl_src.find("addheader("), pl_src.find("->save()"), "addheader() must precede save()")

        perl_bin = _posix_bin("perl")
        if perl_bin is None:
            self.skipTest("POSIX perl required for perl -c and mocked Crypt::PWSafe3 execution.")

        stub_pm = """package Crypt::PWSafe3;
use strict;
use warnings;
sub new { my ($cls, %a) = @_; bless { args => \\%a, records => [], headers => {} }, $cls; }
sub newrecord { my ($self, %r) = @_; push @{$self->{records}}, \\%r; }
sub addheader { my ($self, $h) = @_; $self->{headers}{$h->{name}} = $h->{value}; }
sub markmodified { }
sub save {
    my ($self) = @_;
    open my $fh, ">", $self->{args}{file} or die $!;
    print $fh "COUNT=" . scalar(@{$self->{records}}) . "\\n";
    for my $r (@{$self->{records}}) {
        print $fh join("|", $r->{group}, $r->{title}, $r->{user}, $r->{passwd}) . "\\n";
    }
    print $fh "SAVEDONHOST=" . ($self->{headers}{savedonhost} // "") . "\\n";
    close $fh;
}
sub getheader { my ($self, $k) = @_; bless { val => ($k eq "lastsavetime" ? 1700000000 : $self->{args}{whoami}) }, "Crypt::PWSafe3::Val"; }
package Crypt::PWSafe3::HeaderField;
sub new { my ($cls, %a) = @_; bless \\%a, $cls; }
package Crypt::PWSafe3::Val;
sub value { $_[0]->{val}; }
1;
"""
        with tempfile.TemporaryDirectory() as tmp:
            tpath = pathlib.Path(tmp)
            mod_dir = tpath / "Crypt"
            mod_dir.mkdir()
            (mod_dir / "PWSafe3.pm").write_text(stub_pm, encoding="utf-8")

            syn = subprocess.run(
                [perl_bin, "-c", f"-I{tmp}", str(REPO_ROOT / "convert.pl")],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(syn.returncode, 0, syn.stderr)

            help_res = subprocess.run(
                [perl_bin, f"-I{tmp}", str(REPO_ROOT / "convert.pl"), "--help"],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(help_res.returncode, 0, help_res.stderr)
            self.assertIn("PWSAFE3_PASSWORD", help_res.stdout)

            out_vault = tpath / "demo.psafe3"
            env = os.environ.copy()
            env["PWSAFE3_PASSWORD"] = "mock-secret-passphrase"
            run_res = subprocess.run(
                [perl_bin, f"-I{tmp}", str(REPO_ROOT / "convert.pl"), str(REPO_ROOT / "input.tsv"), str(out_vault)],
                env=env,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(run_res.returncode, 0, run_res.stderr)
            vault_dump = out_vault.read_text(encoding="utf-8")
            self.assertIn("COUNT=4", vault_dump)
            self.assertIn("APP_TESTING|appbddlir1|apps_ro@calcul|azeazezaedsd", vault_dump)
            self.assertIn("APP_PROD|appbddsrv1|calcul@calcul|azeazezaedsd", vault_dump)
            self.assertIn("SAVEDONHOST=localhost", vault_dump)

            # Overwrite guard must reject existing output path
            dup_res = subprocess.run(
                [perl_bin, f"-I{tmp}", str(REPO_ROOT / "convert.pl"), str(REPO_ROOT / "input.tsv"), str(out_vault)],
                env=env,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertNotEqual(dup_res.returncode, 0)


class TestDocsDiataxisSTEAndDiagrams(unittest.TestCase):
    """Validate Diataxis structure, ASD-STE100 rules, relative links, Mermaid, and English isolation."""

    def test_diataxis_structure_ste_and_english_isolation(self) -> None:
        self.assertTrue((DOCS_DIR / "index.md").is_file())
        for q in REQUIRED_QUADRANTS:
            qdir = DOCS_DIR / q
            self.assertTrue(qdir.is_dir())
            self.assertTrue((qdir / "index.md").is_file())
            self.assertTrue([p for p in qdir.glob("*.md") if p.name != "index.md"])

        howtos = [p for p in (DOCS_DIR / "02-how-to-guides").glob("*.md") if p.name != "index.md"]
        for md in howtos:
            non_code, _, _ = _split_fenced_blocks(md.read_text(encoding="utf-8"))
            body = "\n".join(ln for _, ln in non_code)
            self.assertRegex(body, r"(?im)^##\s+Validation")
            self.assertRegex(body, r"(?im)^##\s+Rollback")
            for lineno, line in non_code:
                s = line.strip()
                if not s or s.startswith(("#", "|", "NOTE:", ">")):
                    continue
                self.assertNotIn(";", s, f"{md.name}:{lineno}: semicolon violates STE")
                self.assertNotRegex(s, r"\b(should|would|may|might|shall)\b")
                clean = re.sub(r"`[^`]+`|\[([^\]]+)\]\([^)]+\)", r"\1", re.sub(r"^\d+\.\s+|^-\s+", "", s))
                for sent in [p.strip() for p in re.split(r"(?<=[.!?])\s+", clean) if p.strip()]:
                    words = [w for w in sent.split() if re.search(r"[A-Za-z0-9]", w)]
                    self.assertLessEqual(len(words), 20, f"{md.name}:{lineno} > 20 words: {sent}")

        for md in sorted(REPO_ROOT.rglob("*.md")):
            non_code, _, _ = _split_fenced_blocks(md.read_text(encoding="utf-8"))
            prose = "\n".join(ln for _, ln in non_code)
            self.assertNotRegex(prose, r"\b(Type Acces|Voici|Étape|Procédure|Vérification)\b")

    def test_links_fences_zero_ascii_and_mermaid(self) -> None:
        errors: list[str] = []
        mermaid_count = 0
        for md in sorted(REPO_ROOT.rglob("*.md")):
            rel = md.relative_to(REPO_ROOT).as_posix()
            txt = md.read_text(encoding="utf-8")
            non_code, blocks, unclosed = _split_fenced_blocks(txt)
            if unclosed:
                errors.append(f"{rel}: unclosed fenced block")
            if ASCII_BOX_RE.search(txt):
                errors.append(f"{rel}: ASCII/Unicode box diagram found")

            slugs = {_github_anchor_slug(m.group(2)) for _, ln in non_code if (m := HEADING_RE.match(ln))}
            for lineno, line in non_code:
                for m in LINK_RE.finditer(line):
                    tgt = m.group(1).strip().split()[0]
                    if tgt.startswith(("http://", "https://", "mailto:")):
                        continue
                    if tgt.startswith("#"):
                        if tgt[1:] not in slugs:
                            errors.append(f"{rel}:{lineno}: broken anchor {tgt}")
                        continue
                    fpart, _, frag = tgt.partition("#")
                    resolved = (md.parent / unquote(fpart)).resolve()
                    if not (resolved.is_file() or resolved.is_dir()):
                        errors.append(f"{rel}:{lineno}: missing link target {tgt}")
                    elif frag and resolved.is_file():
                        t_nc, _, _ = _split_fenced_blocks(resolved.read_text(encoding="utf-8"))
                        t_slugs = {_github_anchor_slug(hm.group(2)) for _, ln in t_nc if (hm := HEADING_RE.match(ln))}
                        if frag not in t_slugs:
                            errors.append(f"{rel}:{lineno}: broken target anchor #{frag}")

            for start_line, lang, code in blocks:
                first_tok = code.strip().splitlines()[0].strip() if code.strip() else ""
                if lang == "mermaid":
                    mermaid_count += 1
                    if not any(first_tok.startswith(pfx) for pfx in MERMAID_TYPES):
                        errors.append(f"{rel}:{start_line}: invalid Mermaid header '{first_tok}'")
                    if code.count("[") != code.count("]") or code.count("{") != code.count("}"):
                        errors.append(f"{rel}:{start_line}: unbalanced Mermaid brackets")
                elif any(first_tok.startswith(pfx) for pfx in MERMAID_TYPES):
                    errors.append(f"{rel}:{start_line}: untagged Mermaid block")

            for lineno, line in enumerate(txt.splitlines(), 1):
                if line.lstrip().startswith("```mermaid") and not line.startswith("```mermaid"):
                    errors.append(f"{rel}:{lineno}: indented ```mermaid fence")

        self.assertGreaterEqual(mermaid_count, 4)
        self.assertEqual(errors, [], "\n".join(errors))


if __name__ == "__main__":
    unittest.main()
