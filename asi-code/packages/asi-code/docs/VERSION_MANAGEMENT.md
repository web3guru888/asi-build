# Version Management System

## Overview

ASI-Code uses a centralized version management system to ensure consistency across all files and prevent version mismatches. This system was implemented to resolve version inconsistencies and provide automated validation.

## Single Source of Truth

The `VERSION` file at the project root serves as the canonical version source. All other version references should derive from or match this file.

```
/VERSION
```

## Version Files and References

The following files contain version information that must be kept in sync:

### Primary Files
- **`VERSION`** - Canonical version source (single line with version number)
- **`package.json`** - NPM package version
- **`README.md`** - Displayed project version
- **`sonar-project.properties`** - SonarQube project version

### Source Code Files
- **`src/cli/index.ts`** - CLI fallback versions
- **`src/config/default-config.ts`** - Application default configuration
- **`src/version.ts`** - Version utility module

## Scripts and Automation

### Version Consistency Check
```bash
npm run version:check
```

This script validates that all version references match the canonical version in the `VERSION` file. It checks:
- package.json version
- README.md version display
- sonar-project.properties version
- Hardcoded fallback versions in source files

### Version Bump Utility
```bash
npm run version:bump <new-version>
```

This script safely updates the version across all files:
- Updates the VERSION file
- Updates package.json
- Updates README.md
- Updates sonar-project.properties
- Updates CLI fallback versions
- Updates default configuration
- Runs consistency validation

Example:
```bash
npm run version:bump 0.3.0
```

### Quality Check Integration

Version consistency is integrated into the quality check workflow:
```bash
npm run quality:check
```

This runs the version check along with typecheck, lint, and format checks.

### Pre-commit Hook

A pre-commit hook automatically validates version consistency before each commit:
```bash
# .husky/pre-commit
npm run version:check
```

## Version Utility Module

The `src/version.ts` module provides programmatic access to version information:

```typescript
import { getVersion, getVersionInfo } from './version.js';

// Get current version
const version = getVersion(); // "0.2.0"

// Get structured version info
const info = getVersionInfo();
console.log(info.major); // 0
console.log(info.minor); // 2
console.log(info.patch); // 0
```

## Best Practices

### When Adding New Version References

1. **Avoid hardcoded versions** - Use the version utility module when possible
2. **Update the version check script** - Add new files to `scripts/version-check.js`
3. **Update the version bump script** - Add new files to `scripts/version-bump.js`

### Version Update Workflow

1. **Use the version bump script** instead of manual updates:
   ```bash
   npm run version:bump 1.0.0
   ```

2. **Review changes** before committing:
   ```bash
   git diff
   ```

3. **Run tests** to ensure functionality:
   ```bash
   npm run build && npm test
   ```

4. **Commit and tag**:
   ```bash
   git add .
   git commit -m "bump version to 1.0.0"
   git tag v1.0.0
   ```

### CI/CD Integration

The version check is integrated into:
- **Pre-commit hooks** - Prevents inconsistent commits
- **Quality checks** - Part of the quality gate
- **CI pipeline** - Validates consistency in build process

## Error Handling

If version inconsistencies are detected:

1. **Review the error output** from `npm run version:check`
2. **Use the version bump script** to fix all references
3. **Manually fix** any remaining inconsistencies
4. **Re-run the check** to verify fixes

## Migration from Legacy Versions

This system was implemented to resolve the following inconsistencies found in the codebase:
- README.md showed version 0.2.0
- package.json showed version 0.1.0
- Various source files had hardcoded fallback versions

The canonical version was determined to be **0.2.0** based on:
- Project status (25% Production Ready)
- README.md prominence
- Default configuration usage
- Developer documentation references

## Maintenance

Regular maintenance should include:
- **Periodic audits** of version references
- **Updates to scripts** when new version-containing files are added
- **Testing of version bump workflow** before major releases
- **Documentation updates** when workflow changes

---

This version management system ensures consistency, prevents regressions, and provides automation for version updates across the ASI-Code project.