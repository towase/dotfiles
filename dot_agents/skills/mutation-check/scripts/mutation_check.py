#!/usr/bin/env python3
"""mutation-check skill の補助 CLI。差分範囲の算出、Stryker 設定の生成、mutation.json の要約を行う。"""
import argparse
import fnmatch
import json
import os
import re
import subprocess
import sys

STRYKER_VERSION = "10.1.1"

CODE_LANGS = {
    ".js": "js", ".jsx": "js", ".mjs": "js", ".cjs": "js",
    ".ts": "ts", ".tsx": "ts", ".mts": "ts", ".cts": "ts",
    ".go": "go", ".kt": "kotlin", ".java": "java", ".php": "php",
    ".py": "python", ".sh": "shell", ".bash": "shell", ".rb": "ruby",
    ".rs": "rust", ".awk": "awk", ".swift": "swift", ".vue": "vue",
    ".svelte": "svelte",
}
E2E_DIRS = {"cypress", "e2e", "playwright"}
TEST_DIRS = {"__tests__", "test", "tests", "spec"}
TEST_PATTERNS = [
    "*.test.*", "*.spec.*", "*_test.go", "test_*.py", "*_test.py", "*_spec.rb",
    "*Test.kt", "*Tests.kt", "*Spec.kt", "*Test.java", "*Tests.java", "*Test.php",
    "*.test.sh", "test-*.sh", "test_*.sh", "*.bats",
]
TEST_GLOB_EXTS = "{js,jsx,ts,tsx,mjs,cjs,mts,cts}"
JEST_CONFIGS = ["js", "mjs", "cjs", "ts", "mts", "cts", "json"]
UNSUPPORTED_LOCKS = ["pnpm-lock.yaml", "yarn.lock", "bun.lockb", "bun.lock"]
NPM_LOCKS = ["package-lock.json", "npm-shrinkwrap.json"]
KNOWN_STATUSES = ["Killed", "Survived", "NoCoverage", "Timeout", "RuntimeError", "CompileError", "Ignored", "Pending"]


class UsageError(Exception):
    """前提条件・引数の誤り。exit 2 で終了する。"""


def warn(msg):
    sys.stderr.write(msg + "\n")


def run_git(args, cwd, check=True):
    res = subprocess.run(["git"] + args, cwd=cwd, capture_output=True)
    if check and res.returncode != 0:
        raise UsageError(
            "git %s に失敗しました: %s\ngit リポジトリ内で実行しているか確認してください。"
            % (" ".join(args[:2]), res.stderr.decode("utf-8", "replace").strip())
        )
    return res


def git_text(args, cwd):
    return run_git(args, cwd).stdout.decode("utf-8", "replace").strip()


# ---- ranges ----

def classify(path):
    parts = path.split("/")
    base = parts[-1]
    dirs = parts[:-1]
    if any(d in E2E_DIRS for d in dirs) or fnmatch.fnmatchcase(base, "*.cy.*"):
        return "e2e", None
    ext = os.path.splitext(base)[1]
    lang = CODE_LANGS.get(ext)
    if base.endswith(".d.ts") or lang is None:
        return "other", None
    is_test = (
        any(fnmatch.fnmatchcase(base, p) for p in TEST_PATTERNS)
        or any(d in TEST_DIRS for d in dirs)
        or path.startswith("src/test/")
        or "/src/test/" in path
    )
    return ("test" if is_test else "production"), lang


def merge_ranges(ranges):
    merged = []
    for start, end in sorted(ranges):
        if merged and start <= merged[-1][1] + 1:
            merged[-1][1] = max(merged[-1][1], end)
        else:
            merged.append([start, end])
    return merged


HUNK_RE = re.compile(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,(\d+))? @@")


def parse_diff(text):
    files = {}
    current = None
    for line in text.split("\n"):
        if line.startswith("+++ "):
            target = line[4:].rstrip("\t")
            current = target[2:] if target.startswith("b/") else None
            if current is not None:
                files.setdefault(current, [])
        elif line.startswith("@@") and current is not None:
            m = HUNK_RE.match(line)
            if not m:
                continue
            start = int(m.group(1))
            count = 1 if m.group(2) is None else int(m.group(2))
            if count > 0:
                files[current].append((start, start + count - 1))
    return files


def count_lines(path):
    try:
        with open(path, "rb") as f:
            data = f.read()
    except OSError:
        return 0
    if not data:
        return 0
    return data.count(b"\n") + (0 if data.endswith(b"\n") else 1)


def parse_status_paths(raw):
    entries = raw.split(b"\0")
    paths = []
    i = 0
    while i < len(entries):
        e = entries[i]
        i += 1
        if len(e) < 4:
            continue
        xy = e[:2].decode("ascii", "replace")
        paths.append(e[3:].decode("utf-8", "replace"))
        if "R" in xy or "C" in xy:
            i += 1  # 次のエントリは rename 元パス
    return sorted(set(paths))


def cmd_ranges(args):
    cwd = os.getcwd()
    repo_root = os.path.realpath(git_text(["rev-parse", "--show-toplevel"], cwd))
    head = git_text(["rev-parse", "HEAD"], repo_root)
    mb = run_git(["merge-base", args.base, "HEAD"], repo_root, check=False)
    if mb.returncode != 0:
        raise UsageError(
            "--base '%s' との merge-base を取得できませんでした。--base の指定を確認するか、"
            "git fetch でリモートの ref を取得してから再実行してください。" % args.base
        )
    merge_base = mb.stdout.decode().strip()

    diff = run_git(
        ["-c", "core.quotePath=false", "diff", "-U0", "--no-color", "--no-ext-diff",
         "--src-prefix=a/", "--dst-prefix=b/", "--find-renames", "--diff-filter=d", merge_base, "--"],
        repo_root,
    ).stdout.decode("utf-8", "replace")
    file_ranges = parse_diff(diff)

    untracked = run_git(["ls-files", "--others", "--exclude-standard", "-z"], repo_root).stdout
    for rel in untracked.split(b"\0"):
        if not rel:
            continue
        rel = rel.decode("utf-8", "replace")
        n = count_lines(os.path.join(repo_root, rel))
        file_ranges[rel] = [(1, n)] if n > 0 else []

    status = run_git(["status", "--porcelain=v1", "-z", "-uall"], repo_root).stdout
    dirty = parse_status_paths(status)

    root = repo_root
    if args.root:
        root = os.path.realpath(os.path.join(cwd, args.root))
    root_rel = os.path.relpath(root, repo_root)
    if root_rel == ".." or root_rel.startswith("../"):
        raise UsageError("--root '%s' は git リポジトリの外です。リポジトリ内のディレクトリを指定してください。" % args.root)
    prefix = "" if root_rel == "." else root_rel + "/"

    production, tests, e2e, other = [], [], [], []
    for path in sorted(file_ranges):
        if prefix and not path.startswith(prefix):
            continue
        rel = path[len(prefix):]
        kind, lang = classify(rel)
        stryker = lang in ("js", "ts")
        if kind == "e2e":
            e2e.append(rel)
        elif kind == "other":
            other.append(rel)
        elif kind == "test":
            tests.append({"path": rel, "lang": lang, "stryker": stryker})
        else:
            ranges = merge_ranges(file_ranges[path])
            if ranges:
                production.append({"path": rel, "lang": lang, "stryker": stryker, "ranges": ranges})

    out = {
        "repo_root": repo_root, "root": root, "base": args.base,
        "merge_base": merge_base, "head": head, "dirty": dirty,
        "production": production, "tests": tests, "e2e": e2e, "other": other,
    }
    print(json.dumps(out, indent=2, ensure_ascii=False))


# ---- stryker-config ----

def walk_up(start, stop):
    cur = start
    while True:
        yield cur
        parent = os.path.dirname(cur)
        if cur == stop or parent == cur:
            return
        cur = parent


def under(path, base):
    rel = os.path.relpath(path, base)
    return None if rel == ".." or rel.startswith("../") else rel


def detect_runner(pkg, explicit):
    if explicit:
        return explicit
    with open(os.path.join(pkg, "package.json")) as f:
        data = json.load(f)
    deps = dict(data.get("dependencies") or {})
    deps.update(data.get("devDependencies") or {})
    has_vitest, has_jest = "vitest" in deps, "jest" in deps
    if has_vitest and has_jest:
        raise UsageError("package.json に vitest と jest の両方があります。--runner vitest または --runner jest で指定してください。")
    if has_vitest:
        return "vitest"
    if has_jest:
        return "jest"
    raise UsageError("package.json から vitest / jest を検出できませんでした。--runner vitest または --runner jest で指定してください。")


def check_package_manager(pkg, repo_root):
    for d in walk_up(pkg, repo_root):
        bad = [n for n in UNSUPPORTED_LOCKS if os.path.exists(os.path.join(d, n))]
        if bad:
            raise UsageError(
                "%s が見つかりました。Stryker は `npm i --no-save` で導入するため npm のみ対応です。"
                "手動モード（references/manual.md）を使うか、ユーザーに導入方法を確認してください。" % bad[0]
            )
        if any(os.path.exists(os.path.join(d, n)) for n in NPM_LOCKS):
            return
    warn("警告: lockfile が見つかりません。npm で導入しますが、依存のバージョンが固定されていない可能性があります。")


def typescript_major(pkg, repo_root):
    for d in walk_up(pkg, repo_root):
        p = os.path.join(d, "node_modules", "typescript", "package.json")
        if os.path.isfile(p):
            try:
                with open(p) as f:
                    return int(str(json.load(f).get("version", "0")).split(".")[0])
            except (ValueError, OSError):
                return None
    return None


def cmd_stryker_config(args):
    cwd = os.getcwd()
    pkg = os.path.realpath(os.path.join(cwd, args.pkg))
    if not os.path.isfile(os.path.join(pkg, "package.json")):
        raise UsageError("--pkg '%s' に package.json がありません。package.json があるディレクトリを指定してください。" % args.pkg)
    try:
        with open(args.ranges) as f:
            ranges = json.load(f)
    except (OSError, ValueError) as e:
        raise UsageError("--ranges '%s' を読めませんでした（%s）。`ranges` サブコマンドの出力を保存して指定してください。" % (args.ranges, e))
    root = ranges["root"]
    repo_root = ranges.get("repo_root", root)

    def to_pkg_rel(path):
        return under(os.path.join(root, path), pkg)

    mutate, outside = [], []
    for p in ranges.get("production", []):
        if not p.get("stryker"):
            continue
        rel = to_pkg_rel(p["path"])
        if rel is None:
            outside.append(os.path.relpath(os.path.join(root, p["path"]), repo_root))
            continue
        for start, end in p["ranges"]:
            mutate.append("%s:%d-%d" % (rel, start, end))
    if outside:
        warn("警告: --pkg の外にある TS/JS の変更ファイルは対象外です。別の --pkg で再実行してください:\n  " + "\n  ".join(outside))
    if not mutate:
        raise UsageError(
            "--pkg '%s' 配下に TS/JS の本番コードの変更がありません。他言語は手動モード（references/manual.md）を使ってください。" % args.pkg
        )

    if args.tests:
        tests = []
        for t in args.tests:
            rel = under(os.path.realpath(os.path.join(cwd, t)), pkg)
            if rel is None:
                raise UsageError("--tests '%s' が --pkg の外にあります。--pkg 配下のテストファイルを指定してください。" % t)
            tests.append(rel)
    else:
        tests = []
        for t in ranges.get("tests", []):
            rel = to_pkg_rel(t["path"]) if t.get("stryker") else None
            if rel is not None:
                tests.append(rel)
    if not tests:
        raise UsageError("差分に TS/JS のテストファイルがありません。評価したいテストを --tests で指定してください。")

    runner = detect_runner(pkg, args.runner)
    check_package_manager(pkg, repo_root)

    workdir = os.path.abspath(os.path.join(cwd, args.workdir))
    os.makedirs(workdir, exist_ok=True)
    config = {
        "testRunner": runner,
        "mutate": mutate,
        # testFiles は静的ミュータントを偽 Survived にするため使わず、対象外テストをサンドボックスから除外する
        "ignorePatterns": [
            "**/*.test.%s" % TEST_GLOB_EXTS,
            "**/*.spec.%s" % TEST_GLOB_EXTS,
            "**/__tests__/**/*.%s" % TEST_GLOB_EXTS,
        ] + ["!" + t for t in tests],
        "reporters": ["clear-text", "json", "html"],
        "jsonReporter": {"fileName": workdir + "/mutation.json"},
        "htmlReporter": {"fileName": workdir + "/stryker-report.html"},
        "tempDirName": workdir + "/stryker-tmp",
        "cleanTempDir": "always",
    }
    if runner == "jest":
        jest = {"projectType": "custom"}
        for ext in JEST_CONFIGS:
            name = "jest.config." + ext
            if os.path.isfile(os.path.join(pkg, name)):
                jest["configFile"] = name
                break
        config["jest"] = jest
    if args.concurrency is not None:
        config["concurrency"] = args.concurrency
    major = typescript_major(pkg, repo_root)
    if major is not None and major >= 7:
        # TS 7 では Stryker の tsconfig 前処理が落ちる。ファイルが無ければ前処理自体が skip される
        config["tsconfigFile"] = workdir + "/no-tsconfig.json"

    config_path = workdir + "/stryker.conf.json"
    with open(config_path, "w") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)
        f.write("\n")

    runner_pkg = "@stryker-mutator/%s-runner@%s" % (runner, STRYKER_VERSION)
    out = {
        "config": config_path,
        "cwd": pkg,
        "runner": runner,
        "install": "npm i --no-save --no-audit --no-fund @stryker-mutator/core@%s %s" % (STRYKER_VERSION, runner_pkg),
        "run": "npx stryker run " + config_path,
        "mutate": mutate,
        "tests": tests,
    }
    print(json.dumps(out, indent=2, ensure_ascii=False))


# ---- summarize ----

def load_report(path):
    try:
        with open(path) as f:
            data = json.load(f)
    except (OSError, ValueError) as e:
        raise UsageError("'%s' を読めませんでした（%s）。Stryker が出力した mutation.json のパスを指定してください。" % (path, e))
    if not isinstance(data, dict) or not isinstance(data.get("files"), dict):
        raise UsageError("'%s' は mutation-testing-report 形式ではありません。Stryker の json reporter の出力を指定してください。" % path)
    return data


def count_statuses(mutants):
    counts = {s: 0 for s in KNOWN_STATUSES}
    for m in mutants:
        counts[m["status"]] = counts.get(m["status"], 0) + 1
    return counts


def pct(num, den):
    return round(num / den * 100, 2) if den else None


def scores(counts):
    detected = counts.get("Killed", 0) + counts.get("Timeout", 0)
    surv = counts.get("Survived", 0)
    nocov = counts.get("NoCoverage", 0)
    return pct(detected, detected + surv + nocov), pct(detected, detected + surv)


def mutant_key(file, m):
    loc = m["location"]
    return (file, m["mutatorName"], m.get("replacement"),
            loc["start"]["line"], loc["start"]["column"], loc["end"]["line"], loc["end"]["column"])


def build_summary(report):
    test_names = {}
    for tf in (report.get("testFiles") or {}).values():
        for t in tf.get("tests", []):
            test_names[t["id"]] = t.get("name", t["id"])

    all_mutants = []
    per_file = {}
    undetected, errors = [], []
    for file, fdata in report["files"].items():
        mutants = fdata.get("mutants", [])
        per_file[file] = count_statuses(mutants)
        per_file[file]["mutants"] = len(mutants)
        lines = fdata.get("source", "").split("\n")
        for m in mutants:
            all_mutants.append(m)
            loc = m["location"]
            line = loc["start"]["line"]
            if m["status"] in ("Survived", "NoCoverage"):
                undetected.append({
                    "file": file, "id": m["id"], "status": m["status"],
                    "mutator": m["mutatorName"], "replacement": m.get("replacement"),
                    "line": line, "column": loc["start"]["column"], "end_line": loc["end"]["line"],
                    "static": bool(m.get("static")),
                    "line_text": lines[line - 1].strip() if 0 < line <= len(lines) else "",
                    "covered_by": [test_names.get(i, i) for i in m.get("coveredBy") or []],
                })
            elif m["status"] in ("RuntimeError", "CompileError"):
                reason = (m.get("statusReason") or "").split("\n")[0][:300]
                errors.append({
                    "file": file, "id": m["id"], "status": m["status"], "line": line,
                    "mutator": m["mutatorName"], "reason": reason,
                })
    totals = count_statuses(all_mutants)
    totals["mutants"] = len(all_mutants)
    score, covered = scores(totals)
    undetected.sort(key=lambda u: (u["file"], u["line"], u["column"]))
    errors.sort(key=lambda e: (e["file"], e["line"]))
    return {
        "totals": totals, "score": score, "covered_score": covered,
        "files": per_file, "undetected": undetected, "errors": errors,
    }


def build_changes(before, after):
    after_status = {}
    for file, fdata in after["files"].items():
        for m in fdata.get("mutants", []):
            after_status[mutant_key(file, m)] = m["status"]
    changes = []
    for file, fdata in before["files"].items():
        for m in fdata.get("mutants", []):
            if m["status"] not in ("Survived", "NoCoverage"):
                continue
            key = mutant_key(file, m)
            changes.append({
                "file": file, "line": key[3], "column": key[4], "mutator": m["mutatorName"],
                "replacement": m.get("replacement"), "before": m["status"],
                "after": after_status.get(key, "missing"),
            })
    changes.sort(key=lambda c: (c["file"], c["line"], c["column"]))
    return changes


def md_cell(value, limit=80):
    s = str(value).replace("\n", " ").replace("|", "\\|")
    return s if len(s) <= limit else s[: limit - 1] + "…"


def fmt_score(v):
    return "n/a" if v is None else "%s%%" % v


def render_md(s):
    t = s["totals"]
    parts = ["- " + ", ".join("%s %d" % (k, v) for k, v in t.items() if v or k == "mutants")]
    parts[0] = "- 合計: " + parts[0][2:]
    parts.append("- スコア: %s（covered: %s）" % (fmt_score(s["score"]), fmt_score(s["covered_score"])))
    if "before_score" in s:
        parts.append("- 変更前スコア: %s" % fmt_score(s["before_score"]))
    out = ["## Mutation 結果", ""] + parts + [""]
    out.append("### 検出されなかったミュータント (%d)" % len(s["undetected"]))
    if s["undetected"]:
        # 同じ行に同じ mutator の変異が複数あるので、列まで出して見分けられるようにする
        out += ["", "| file | line:col | status | mutator | replacement | line_text | covered_by |", "|---|---|---|---|---|---|---|"]
        for u in s["undetected"]:
            out.append("| %s | %d:%d | %s | %s | `%s` | `%s` | %s |" % (
                md_cell(u["file"]), u["line"], u["column"], u["status"], u["mutator"],
                md_cell(u["replacement"], 60).replace("`", "'"), md_cell(u["line_text"], 60).replace("`", "'"),
                md_cell(", ".join(u["covered_by"]), 60)))
    out.append("")
    if s["errors"]:
        out += ["### エラーになったミュータント (%d)" % len(s["errors"]), "",
                "| file | line | status | mutator | reason |", "|---|---|---|---|---|"]
        for e in s["errors"]:
            out.append("| %s | %d | %s | %s | %s |" % (md_cell(e["file"]), e["line"], e["status"], e["mutator"], md_cell(e["reason"], 100)))
        out.append("")
    if "changes" in s:
        out += ["### 変更前との比較 (%d)" % len(s["changes"]), ""]
        if s["changes"]:
            out += ["| file | line:col | mutator | replacement | before | after |", "|---|---|---|---|---|---|"]
            for c in s["changes"]:
                out.append("| %s | %d:%d | %s | `%s` | %s | %s |" % (
                    md_cell(c["file"]), c["line"], c["column"], c["mutator"], md_cell(c["replacement"], 60).replace("`", "'"),
                    c["before"], c["after"]))
            out.append("")
    return "\n".join(out)


def cmd_summarize(args):
    summary = build_summary(load_report(args.mutation_json))
    if args.before:
        before_report = load_report(args.before)
        before = build_summary(before_report)
        summary["before_totals"] = before["totals"]
        summary["before_score"] = before["score"]
        summary["changes"] = build_changes(before_report, load_report(args.mutation_json))
    if args.format == "md":
        print(render_md(summary))
    else:
        print(json.dumps(summary, indent=2, ensure_ascii=False))


# ---- entrypoint ----

def build_parser():
    p = argparse.ArgumentParser(prog="mutation_check.py", description="mutation-check skill の補助 CLI")
    sub = p.add_subparsers(dest="cmd", required=True)

    r = sub.add_parser("ranges", help="base との差分範囲を JSON で出力する")
    r.add_argument("--base", required=True, help="比較元の ref（例: main, origin/main）")
    r.add_argument("--root", help="この配下のファイルだけに絞る（パスは root 相対で出力）")
    r.set_defaults(func=cmd_ranges)

    c = sub.add_parser("stryker-config", help="Stryker 設定ファイルを生成する")
    c.add_argument("--ranges", required=True, help="ranges サブコマンドの出力 JSON")
    c.add_argument("--pkg", required=True, help="package.json があるディレクトリ")
    c.add_argument("--workdir", required=True, help="設定・レポートの出力先（リポジトリ外）")
    c.add_argument("--runner", choices=["vitest", "jest"])
    c.add_argument("--tests", nargs="+", help="評価対象のテスト（指定時は差分のテストを使わない）")
    c.add_argument("--concurrency", type=int)
    c.set_defaults(func=cmd_stryker_config)

    s = sub.add_parser("summarize", help="mutation.json を要約する")
    s.add_argument("mutation_json")
    s.add_argument("--before", help="比較元の mutation.json")
    s.add_argument("--format", choices=["json", "md"], default="json")
    s.set_defaults(func=cmd_summarize)
    return p


def main(argv=None):
    args = build_parser().parse_args(argv)
    try:
        args.func(args)
    except UsageError as e:
        warn("エラー: %s" % e)
        return 2
    except BrokenPipeError:
        return 0
    except Exception as e:  # noqa: BLE001 想定外は原因調査用に型名つきで出す
        warn("予期しないエラー: %s: %s\n再現手順を添えて報告してください。" % (type(e).__name__, e))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
