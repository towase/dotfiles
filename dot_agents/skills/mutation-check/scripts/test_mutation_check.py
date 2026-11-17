"""mutation_check.py の CLI テスト。サブプロセス経由で呼び、__pycache__ を残さない。"""
import copy
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(HERE, "mutation_check.py")

GIT_ENV = dict(os.environ)
GIT_ENV.update(
    {
        "GIT_CONFIG_GLOBAL": "/dev/null",
        "GIT_CONFIG_NOSYSTEM": "1",
        "PYTHONDONTWRITEBYTECODE": "1",
    }
)


def run_cli(*args, cwd=None):
    return subprocess.run(
        [sys.executable, "-B", SCRIPT] + list(args),
        capture_output=True,
        text=True,
        cwd=cwd,
        env=GIT_ENV,
    )


def git(repo, *args):
    subprocess.run(
        ["git"] + list(args),
        cwd=repo,
        env=GIT_ENV,
        check=True,
        capture_output=True,
        text=True,
    )


def write(base, rel, content):
    path = os.path.join(base, rel)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        f.write(content)
    return path


def numbered(n, prefix="line"):
    return "".join("%s %d\n" % (prefix, i) for i in range(1, n + 1))


def replace_lines(text, changes):
    lines = text.splitlines(True)
    for no, new in changes.items():
        lines[no - 1] = new + "\n"
    return "".join(lines)


class TempDirCase(unittest.TestCase):
    def make_tmp(self):
        tmp = os.path.realpath(tempfile.mkdtemp(prefix="mutcheck-"))
        self.addCleanup(shutil.rmtree, tmp, True)
        return tmp


class RangesTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = os.path.realpath(tempfile.mkdtemp(prefix="mutcheck-repo-"))
        r = cls.repo = os.path.join(cls.tmp, "repo")
        os.makedirs(r)
        git(r, "init", "-q", "-b", "main")
        git(r, "config", "user.name", "t")
        git(r, "config", "user.email", "t@example.com")
        git(r, "config", "commit.gpgsign", "false")
        cls.a_src = numbered(30)
        write(r, "src/a.ts", cls.a_src)
        write(r, "src/a.test.ts", numbered(2, "t"))
        write(r, "src/del.ts", numbered(10))
        write(r, "src/other.ts", numbered(5))
        write(r, "src/c.ts", numbered(5))
        write(r, "README.md", "readme\n")
        write(r, "frontend/src/f.ts", numbered(5))
        write(r, "svc/x.go", numbered(5))
        git(r, "add", "-A")
        git(r, "commit", "-q", "-m", "init")
        git(r, "checkout", "-q", "-b", "feature")
        write(r, "src/a.ts", replace_lines(cls.a_src, {3: "changed 3", 20: "changed 20", 21: "changed 21"}))
        write(r, "src/del.ts", "".join(l for i, l in enumerate(numbered(10).splitlines(True), 1) if i not in (5, 6)))
        write(r, "src/a.test.ts", numbered(2, "t") + "t 3\n")
        write(r, "frontend/src/f.ts", replace_lines(numbered(5), {2: "changed"}))
        write(r, "README.md", "readme changed\n")
        for rel in [
            "src/__tests__/b.ts",
            "core/src/test/kotlin/FooTest.kt",
            "pkg/x_test.go",
            "scripts/test-foo.sh",
            "types.d.ts",
            "cypress/e2e/a.cy.ts",
            "build.gradle.kts",
        ]:
            write(r, rel, "x\ny\n")
        git(r, "add", "-A")
        git(r, "commit", "-q", "-m", "feature")
        # base 側の後追いコミットは merge-base により除外されるはず
        git(r, "checkout", "-q", "main")
        write(r, "src/other.ts", replace_lines(numbered(5), {1: "main change"}))
        git(r, "commit", "-q", "-am", "main moves on")
        git(r, "checkout", "-q", "feature")
        # 未コミット: 追跡ファイルの変更と未追跡の新規ファイル
        write(r, "src/c.ts", replace_lines(numbered(5), {2: "dirty"}))
        write(r, "src/new.ts", "a\nb\nc\n")
        res = run_cli("ranges", "--base", "main", cwd=r)
        assert res.returncode == 0, res.stderr
        cls.out = json.loads(res.stdout)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, True)

    def prod(self, path):
        for p in self.out["production"]:
            if p["path"] == path:
                return p
        return None

    def test_header_fields(self):
        o = self.out
        self.assertEqual(o["repo_root"], self.repo)
        self.assertEqual(o["root"], self.repo)
        self.assertEqual(o["base"], "main")
        self.assertEqual(len(o["merge_base"]), 40)
        self.assertEqual(len(o["head"]), 40)
        self.assertNotEqual(o["merge_base"], o["head"])

    def test_multi_hunk_ranges(self):
        p = self.prod("src/a.ts")
        self.assertEqual(p["ranges"], [[3, 3], [20, 21]])
        self.assertEqual(p["lang"], "ts")
        self.assertTrue(p["stryker"])

    def test_pure_deletion_has_no_entry(self):
        self.assertIsNone(self.prod("src/del.ts"))

    def test_uncommitted_change_included(self):
        self.assertEqual(self.prod("src/c.ts")["ranges"], [[2, 2]])

    def test_untracked_file_whole_range(self):
        self.assertEqual(self.prod("src/new.ts")["ranges"], [[1, 3]])

    def test_base_branch_changes_excluded(self):
        self.assertIsNone(self.prod("src/other.ts"))

    def test_classification(self):
        o = self.out
        tests = {t["path"]: t for t in o["tests"]}
        for path in [
            "src/a.test.ts",
            "src/__tests__/b.ts",
            "core/src/test/kotlin/FooTest.kt",
            "pkg/x_test.go",
            "scripts/test-foo.sh",
        ]:
            self.assertIn(path, tests)
        self.assertEqual(tests["src/a.test.ts"]["lang"], "ts")
        self.assertTrue(tests["src/a.test.ts"]["stryker"])
        self.assertEqual(tests["core/src/test/kotlin/FooTest.kt"]["lang"], "kotlin")
        self.assertFalse(tests["core/src/test/kotlin/FooTest.kt"]["stryker"])
        self.assertEqual(tests["pkg/x_test.go"]["lang"], "go")
        self.assertEqual(tests["scripts/test-foo.sh"]["lang"], "shell")
        self.assertEqual(o["e2e"], ["cypress/e2e/a.cy.ts"])
        for path in ["types.d.ts", "build.gradle.kts", "README.md"]:
            self.assertIn(path, o["other"])
        self.assertNotIn("README.md", [p["path"] for p in o["production"]])

    def test_lists_sorted(self):
        paths = [p["path"] for p in self.out["production"]]
        self.assertEqual(paths, sorted(paths))
        tpaths = [p["path"] for p in self.out["tests"]]
        self.assertEqual(tpaths, sorted(tpaths))

    def test_dirty_list(self):
        self.assertEqual(self.out["dirty"], sorted(["src/c.ts", "src/new.ts"]))

    def test_root_filter_relative_paths(self):
        res = run_cli("ranges", "--base", "main", "--root", "frontend", cwd=self.repo)
        self.assertEqual(res.returncode, 0, res.stderr)
        o = json.loads(res.stdout)
        self.assertEqual(o["root"], os.path.join(self.repo, "frontend"))
        self.assertEqual(o["repo_root"], self.repo)
        self.assertEqual([p["path"] for p in o["production"]], ["src/f.ts"])
        self.assertEqual(o["production"][0]["ranges"], [[2, 2]])
        self.assertEqual(o["tests"], [])
        self.assertEqual(o["other"], [])

    def test_root_dot_from_subdir(self):
        res = run_cli("ranges", "--base", "main", "--root", ".", cwd=os.path.join(self.repo, "frontend"))
        self.assertEqual(res.returncode, 0, res.stderr)
        o = json.loads(res.stdout)
        self.assertEqual([p["path"] for p in o["production"]], ["src/f.ts"])

    def test_bad_base_exit_2(self):
        res = run_cli("ranges", "--base", "no-such-ref", cwd=self.repo)
        self.assertEqual(res.returncode, 2)
        self.assertIn("--base", res.stderr)
        self.assertIn("git fetch", res.stderr)

    def test_not_a_repo_exit_2(self):
        tmp = os.path.realpath(tempfile.mkdtemp(prefix="mutcheck-norepo-"))
        self.addCleanup(shutil.rmtree, tmp, True)
        res = run_cli("ranges", "--base", "main", cwd=tmp)
        self.assertEqual(res.returncode, 2)


class StrykerConfigTest(TempDirCase):
    def setUp(self):
        self.tmp = self.make_tmp()
        self.repo = os.path.join(self.tmp, "repo")
        self.pkg = os.path.join(self.repo, "web")
        self.workdir = os.path.join(self.tmp, "work")
        os.makedirs(self.pkg)
        write(self.pkg, "package.json", json.dumps({"devDependencies": {"vitest": "^2.0.0"}}))
        write(self.repo, "package-lock.json", "{}")

    def ranges_file(self, production=None, tests=None, root=None):
        if production is None:
            production = [
                {"path": "web/src/a.ts", "lang": "ts", "stryker": True, "ranges": [[3, 10], [20, 20]]},
            ]
        if tests is None:
            tests = [{"path": "web/src/a.test.ts", "lang": "ts", "stryker": True}]
        data = {
            "repo_root": self.repo,
            "root": root or self.repo,
            "base": "main",
            "production": production,
            "tests": tests,
        }
        path = os.path.join(self.tmp, "ranges.json")
        with open(path, "w") as f:
            json.dump(data, f)
        return path

    def run_cfg(self, *extra, **kw):
        ranges = kw.get("ranges") or self.ranges_file()
        return run_cli(
            "stryker-config", "--ranges", ranges, "--pkg", self.pkg, "--workdir", self.workdir, *extra,
            cwd=kw.get("cwd"),
        )

    def load_cfg(self, res):
        self.assertEqual(res.returncode, 0, res.stderr)
        out = json.loads(res.stdout)
        with open(out["config"]) as f:
            return out, json.load(f)

    def test_vitest_full_shape(self):
        out, cfg = self.load_cfg(self.run_cfg())
        wd = self.workdir
        self.assertEqual(
            cfg,
            {
                "testRunner": "vitest",
                "mutate": ["src/a.ts:3-10", "src/a.ts:20-20"],
                "ignorePatterns": [
                    "**/*.test.{js,jsx,ts,tsx,mjs,cjs,mts,cts}",
                    "**/*.spec.{js,jsx,ts,tsx,mjs,cjs,mts,cts}",
                    "**/__tests__/**/*.{js,jsx,ts,tsx,mjs,cjs,mts,cts}",
                    "!src/a.test.ts",
                ],
                "reporters": ["clear-text", "json", "html"],
                "jsonReporter": {"fileName": wd + "/mutation.json"},
                "htmlReporter": {"fileName": wd + "/stryker-report.html"},
                "tempDirName": wd + "/stryker-tmp",
                "cleanTempDir": "always",
            },
        )
        self.assertNotIn("testFiles", cfg)
        self.assertEqual(out["config"], wd + "/stryker.conf.json")
        self.assertEqual(out["cwd"], self.pkg)
        self.assertEqual(out["runner"], "vitest")
        self.assertEqual(
            out["install"],
            "npm i --no-save --no-audit --no-fund @stryker-mutator/core@10.1.1 @stryker-mutator/vitest-runner@10.1.1",
        )
        self.assertEqual(out["run"], "npx stryker run " + out["config"])
        self.assertEqual(out["mutate"], ["src/a.ts:3-10", "src/a.ts:20-20"])
        self.assertEqual(out["tests"], ["src/a.test.ts"])

    def test_jest_with_config_file(self):
        write(self.pkg, "package.json", json.dumps({"dependencies": {"jest": "^29"}}))
        write(self.pkg, "jest.config.mjs", "export default {}\n")
        out, cfg = self.load_cfg(self.run_cfg())
        self.assertEqual(cfg["testRunner"], "jest")
        self.assertEqual(cfg["jest"], {"projectType": "custom", "configFile": "jest.config.mjs"})
        self.assertIn("@stryker-mutator/jest-runner@10.1.1", out["install"])

    def test_jest_without_config_file(self):
        write(self.pkg, "package.json", json.dumps({"dependencies": {"jest": "^29"}}))
        _, cfg = self.load_cfg(self.run_cfg())
        self.assertEqual(cfg["jest"], {"projectType": "custom"})

    def test_ts7_sets_missing_tsconfig(self):
        write(self.repo, "node_modules/typescript/package.json", json.dumps({"version": "7.0.1"}))
        _, cfg = self.load_cfg(self.run_cfg())
        self.assertEqual(cfg["tsconfigFile"], self.workdir + "/no-tsconfig.json")
        self.assertFalse(os.path.exists(cfg["tsconfigFile"]))

    def test_ts5_has_no_tsconfig_key(self):
        write(self.pkg, "node_modules/typescript/package.json", json.dumps({"version": "5.6.2"}))
        _, cfg = self.load_cfg(self.run_cfg())
        self.assertNotIn("tsconfigFile", cfg)

    def test_concurrency(self):
        _, cfg = self.load_cfg(self.run_cfg("--concurrency", "2"))
        self.assertEqual(cfg["concurrency"], 2)

    def test_no_tests_exit_2(self):
        res = self.run_cfg(ranges=self.ranges_file(tests=[]))
        self.assertEqual(res.returncode, 2)
        self.assertIn("--tests", res.stderr)

    def test_tests_option_replaces_diff_tests(self):
        write(self.pkg, "src/x.test.ts", "")
        _, cfg = self.load_cfg(self.run_cfg("--tests", os.path.join(self.pkg, "src/x.test.ts")))
        negs = [p for p in cfg["ignorePatterns"] if p.startswith("!")]
        self.assertEqual(negs, ["!src/x.test.ts"])

    def test_tests_option_relative_to_cwd(self):
        write(self.pkg, "src/x.test.ts", "")
        res = self.run_cfg("--tests", "src/x.test.ts", cwd=self.pkg)
        out, _ = self.load_cfg(res)
        self.assertEqual(out["tests"], ["src/x.test.ts"])

    def test_tests_option_works_without_diff_tests(self):
        res = self.run_cfg("--tests", os.path.join(self.pkg, "src/x.test.ts"), ranges=self.ranges_file(tests=[]))
        self.assertEqual(res.returncode, 0, res.stderr)

    def test_no_ts_production_exit_2(self):
        prod = [{"path": "web/main.go", "lang": "go", "stryker": False, "ranges": [[1, 3]]}]
        res = self.run_cfg(ranges=self.ranges_file(production=prod))
        self.assertEqual(res.returncode, 2)
        self.assertIn("manual.md", res.stderr)

    def test_pnpm_lock_exit_2(self):
        os.remove(os.path.join(self.repo, "package-lock.json"))
        write(self.repo, "pnpm-lock.yaml", "")
        res = self.run_cfg()
        self.assertEqual(res.returncode, 2)
        self.assertIn("npm", res.stderr)

    def test_no_lockfile_warns(self):
        os.remove(os.path.join(self.repo, "package-lock.json"))
        res = self.run_cfg()
        self.assertEqual(res.returncode, 0, res.stderr)
        self.assertIn("lock", res.stderr)

    def test_both_runners_exit_2_unless_runner(self):
        write(self.pkg, "package.json", json.dumps({"devDependencies": {"vitest": "1", "jest": "29"}}))
        res = self.run_cfg()
        self.assertEqual(res.returncode, 2)
        self.assertIn("--runner", res.stderr)
        out, cfg = self.load_cfg(self.run_cfg("--runner", "jest"))
        self.assertEqual(cfg["testRunner"], "jest")

    def test_no_runner_exit_2(self):
        write(self.pkg, "package.json", "{}")
        res = self.run_cfg()
        self.assertEqual(res.returncode, 2)
        self.assertIn("--runner", res.stderr)

    def test_missing_package_json_exit_2(self):
        os.remove(os.path.join(self.pkg, "package.json"))
        res = self.run_cfg()
        self.assertEqual(res.returncode, 2)
        self.assertIn("package.json", res.stderr)

    def test_production_outside_pkg_warns(self):
        prod = [
            {"path": "web/src/a.ts", "lang": "ts", "stryker": True, "ranges": [[1, 2]]},
            {"path": "other/src/z.ts", "lang": "ts", "stryker": True, "ranges": [[1, 2]]},
        ]
        res = self.run_cfg(ranges=self.ranges_file(production=prod))
        self.assertEqual(res.returncode, 0, res.stderr)
        self.assertIn("other/src/z.ts", res.stderr)
        out = json.loads(res.stdout)
        self.assertEqual(out["mutate"], ["src/a.ts:1-2"])

    def test_ranges_root_below_repo_root(self):
        prod = [{"path": "src/a.ts", "lang": "ts", "stryker": True, "ranges": [[4, 5]]}]
        tests = [{"path": "src/a.test.ts", "lang": "ts", "stryker": True}]
        rf = self.ranges_file(production=prod, tests=tests, root=self.pkg)
        out, _ = self.load_cfg(self.run_cfg(ranges=rf))
        self.assertEqual(out["mutate"], ["src/a.ts:4-5"])


def make_report(overrides=None, drop=()):
    """最小限の mutation-testing-report。overrides は {mutant id: status}。"""
    src_a = "const a = 1;\n  const x = a + b;\nreturn x;\n"

    def loc(sl, sc, el, ec):
        return {"start": {"line": sl, "column": sc}, "end": {"line": el, "column": ec}}

    mutants = [
        {"id": "1", "mutatorName": "StringLiteral", "replacement": '""', "status": "Killed", "static": False,
         "location": loc(1, 11, 1, 12), "coveredBy": ["t1"], "killedBy": ["t1"]},
        {"id": "2", "mutatorName": "ArithmeticOperator", "replacement": "a - b", "status": "Survived", "static": True,
         "location": loc(2, 13, 2, 18), "coveredBy": ["t1", "t2"]},
        {"id": "3", "mutatorName": "BlockStatement", "replacement": "{}", "status": "NoCoverage", "static": False,
         "location": loc(3, 1, 3, 9)},
        {"id": "4", "mutatorName": "ConditionalExpression", "replacement": "true", "status": "Timeout", "static": False,
         "location": loc(1, 1, 1, 5)},
        {"id": "5", "mutatorName": "ObjectLiteral", "replacement": "{}", "status": "RuntimeError", "static": False,
         "statusReason": "TypeError: boom\n    at foo (x.js:1)", "location": loc(2, 3, 2, 4)},
        {"id": "6", "mutatorName": "EqualityOperator", "replacement": "!==", "status": "CompileError", "static": False,
         "statusReason": "x" * 400, "location": loc(2, 5, 2, 6)},
        {"id": "7", "mutatorName": "StringLiteral", "replacement": "'s'", "status": "Ignored", "static": False,
         "location": loc(3, 2, 3, 3)},
    ]
    mutants = [copy.deepcopy(m) for m in mutants if m["id"] not in drop]
    for m in mutants:
        if overrides and m["id"] in overrides:
            m["status"] = overrides[m["id"]]
    return {
        "schemaVersion": "2",
        "files": {
            "src/a.ts": {"language": "typescript", "source": src_a, "mutants": mutants},
            "src/b.ts": {
                "source": "x\n",
                "mutants": [
                    {"id": "10", "mutatorName": "StringLiteral", "replacement": '""', "status": "Killed",
                     "static": False, "location": loc(1, 1, 1, 2)}
                ],
            },
        },
        "testFiles": {
            "src/a.test.ts": {"tests": [{"id": "t1", "name": "adds"}, {"id": "t2", "name": "subtracts"}]}
        },
    }


class SummarizeTest(TempDirCase):
    def setUp(self):
        self.tmp = self.make_tmp()

    def dump(self, name, data):
        path = os.path.join(self.tmp, name)
        with open(path, "w") as f:
            json.dump(data, f)
        return path

    def summarize(self, *args):
        res = run_cli("summarize", *args)
        self.assertEqual(res.returncode, 0, res.stderr)
        return res

    def test_totals_and_scores(self):
        out = json.loads(self.summarize(self.dump("r.json", make_report())).stdout)
        t = out["totals"]
        self.assertEqual(t["Killed"], 2)
        self.assertEqual(t["Survived"], 1)
        self.assertEqual(t["NoCoverage"], 1)
        self.assertEqual(t["Timeout"], 1)
        self.assertEqual(t["RuntimeError"], 1)
        self.assertEqual(t["CompileError"], 1)
        self.assertEqual(t["Ignored"], 1)
        self.assertEqual(t["mutants"], 8)
        self.assertEqual(out["score"], 60.0)
        self.assertEqual(out["covered_score"], 75.0)
        self.assertEqual(out["files"]["src/a.ts"]["Survived"], 1)
        self.assertEqual(out["files"]["src/b.ts"]["Killed"], 1)

    def test_score_null_when_no_denominator(self):
        rep = {"files": {"a.ts": {"source": "x\n", "mutants": [
            {"id": "1", "mutatorName": "m", "replacement": "r", "status": "Ignored", "static": False,
             "location": {"start": {"line": 1, "column": 1}, "end": {"line": 1, "column": 2}}}]}}}
        out = json.loads(self.summarize(self.dump("r.json", rep)).stdout)
        self.assertIsNone(out["score"])
        self.assertIsNone(out["covered_score"])

    def test_undetected(self):
        out = json.loads(self.summarize(self.dump("r.json", make_report())).stdout)
        und = out["undetected"]
        self.assertEqual([u["id"] for u in und], ["2", "3"])
        u = und[0]
        self.assertEqual(u["file"], "src/a.ts")
        self.assertEqual(u["status"], "Survived")
        self.assertEqual(u["mutator"], "ArithmeticOperator")
        self.assertEqual(u["replacement"], "a - b")
        self.assertEqual((u["line"], u["column"], u["end_line"]), (2, 13, 2))
        self.assertTrue(u["static"])
        self.assertEqual(u["line_text"], "const x = a + b;")
        self.assertEqual(u["covered_by"], ["adds", "subtracts"])
        self.assertEqual(und[1]["covered_by"], [])
        self.assertEqual(und[1]["line_text"], "return x;")

    def test_errors(self):
        out = json.loads(self.summarize(self.dump("r.json", make_report())).stdout)
        errs = {e["id"]: e for e in out["errors"]}
        self.assertEqual(set(errs), {"5", "6"})
        self.assertEqual(errs["5"]["reason"], "TypeError: boom")
        self.assertEqual(errs["5"]["status"], "RuntimeError")
        self.assertEqual(errs["5"]["file"], "src/a.ts")
        self.assertEqual(errs["5"]["line"], 2)
        self.assertEqual(errs["5"]["mutator"], "ObjectLiteral")
        self.assertEqual(len(errs["6"]["reason"]), 300)

    def test_before_changes(self):
        before = self.dump("before.json", make_report())
        after = self.dump("after.json", make_report({"2": "Killed"}, drop=("3",)))
        out = json.loads(self.summarize(after, "--before", before).stdout)
        changes = out["changes"]
        self.assertEqual(len(changes), 2)
        c2 = changes[0]
        self.assertEqual((c2["file"], c2["line"], c2["mutator"], c2["replacement"]),
                         ("src/a.ts", 2, "ArithmeticOperator", "a - b"))
        self.assertEqual((c2["before"], c2["after"]), ("Survived", "Killed"))
        c3 = changes[1]
        self.assertEqual((c3["before"], c3["after"]), ("NoCoverage", "missing"))
        self.assertEqual(out["before_totals"]["Survived"], 1)
        self.assertEqual(out["before_score"], 60.0)

    def test_before_no_coverage_stays(self):
        before = self.dump("before.json", make_report())
        after = self.dump("after.json", make_report({"2": "Killed"}))
        out = json.loads(self.summarize(after, "--before", before).stdout)
        c3 = [c for c in out["changes"] if c["line"] == 3][0]
        self.assertEqual((c3["before"], c3["after"]), ("NoCoverage", "NoCoverage"))

    def test_no_changes_key_without_before(self):
        out = json.loads(self.summarize(self.dump("r.json", make_report())).stdout)
        self.assertNotIn("changes", out)

    def test_markdown_format(self):
        before = self.dump("before.json", make_report())
        after = self.dump("after.json", make_report({"2": "Killed"}))
        res = self.summarize(after, "--before", before, "--format", "md")
        self.assertIn("src/a.ts", res.stdout)
        self.assertIn("Killed", res.stdout)
        self.assertIn("|", res.stdout)
        self.assertIn("RuntimeError", res.stdout)

    def test_markdown_shows_column_to_tell_same_line_mutants_apart(self):
        before = self.dump("before.json", make_report())
        after = self.dump("after.json", make_report({"2": "Killed"}))
        out = self.summarize(after, "--before", before, "--format", "md").stdout
        und = self.summarize(before, "--format", "md").stdout
        self.assertIn("| src/a.ts | 2:13 |", und)
        self.assertIn("| src/a.ts | 2:13 |", out)

    def test_changes_include_column(self):
        before = self.dump("before.json", make_report())
        after = self.dump("after.json", make_report({"2": "Killed"}))
        out = json.loads(self.summarize(after, "--before", before).stdout)
        self.assertEqual(out["changes"][0]["column"], 13)

    def test_missing_file_exit_2(self):
        res = run_cli("summarize", os.path.join(self.tmp, "none.json"))
        self.assertEqual(res.returncode, 2)

    def test_invalid_json_exit_2(self):
        p = os.path.join(self.tmp, "bad.json")
        with open(p, "w") as f:
            f.write("{")
        res = run_cli("summarize", p)
        self.assertEqual(res.returncode, 2)


if __name__ == "__main__":
    unittest.main()
