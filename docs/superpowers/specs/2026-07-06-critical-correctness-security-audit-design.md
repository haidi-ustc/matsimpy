# MatSimPy critical correctness/security audit design

Date: 2026-07-06

## 1. Goal

Review the current MatSimPy project for critical correctness and security bugs that could break users.

This is a read-only audit. The audit must produce a final report in Chinese and must not include code edits unless a later implementation plan is explicitly approved.

## 2. Scope

The review focuses on user-breaking risks:

- Security vulnerabilities, especially unsafe parsing, command execution, network access, and filesystem writes.
- Silent scientific correctness failures, including wrong structures, wrong coordinates, mutation leaks, serialization corruption, or incorrect calculator outputs.
- Public API crashes on valid user input.
- Packaging and optional dependency behavior that causes normal imports or documented workflows to fail.
- Persistence bugs that can corrupt, lose, or misidentify stored user data.

The review excludes ordinary style concerns, broad refactors, naming preferences, and low-severity maintainability issues unless they directly contribute to a critical bug.

## 3. Primary Review Targets

The first-pass targets are:

- `matsimpy/calculator/`: subprocess boundaries, external binary invocation, parser assumptions, optional dependency behavior, and output correctness.
- `matsimpy/io/`: file parsing/writing, path handling, round-trip guarantees, and format registry behavior.
- `matsimpy/storage/`: document identity, serialization, backend contract behavior, and persistence safety.
- `matsimpy/ai/`: network calls, tool execution boundaries, workspace/session persistence, and user-controlled inputs.
- `matsimpy/core/`: immutability contracts, coordinate conversion, structure mutation, serialization, and hash/equality behavior.

Secondary targets include registries, transformations, builders, and configuration when they touch the risks above.

## 4. Audit Method

The audit runs in four passes:

1. Attack surface pass: inspect deserialization, subprocess execution, external command construction, file path reads/writes, network calls, and optional dependency gates.
2. Correctness boundary pass: inspect public API contracts where valid input could produce wrong structures, mutation leaks, coordinate mistakes, registry ambiguity, or serialization failures.
3. Runtime contract pass: check packaging, import behavior, optional extras, and documented workflows for user-facing crashes.
4. Evidence pass: run focused tests, static checks, or small repro snippets for suspected critical issues.

The review should prefer concrete evidence over speculation. A risk that cannot be dynamically reproduced may still be reported if the code path and impact are clear, but the report must label it as not dynamically reproduced.

## 5. Report Format

The final report must be written in Chinese only.

Findings must be ordered by severity and include:

- Affected file and line.
- Impact.
- Evidence.
- User-facing failure mode.
- Recommended remediation.
- Verification status.

If no critical issue is found in a reviewed area, mention that briefly without padding the report with low-priority cleanup.

The report ends with:

- `已验证`: commands, tests, or snippets that were run.
- `未验证`: gaps, skipped checks, optional dependencies, or limits of the audit.

## 6. Success Criteria

The audit is complete when:

- Critical security and correctness risk surfaces have been inspected.
- Every reported issue has file/line evidence.
- Suspected issues are verified with focused tests or clearly marked as evidence-backed but not dynamically reproduced.
- The final report is in Chinese and does not include unrelated style or refactor findings.

