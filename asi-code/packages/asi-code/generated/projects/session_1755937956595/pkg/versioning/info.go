package versioning

import (
	"fmt"
	"regexp"
	"sort"
	"strconv"
	"strings"
	"time"

	"mlops-platform/internal/config"
	"mlops-platform/internal/logging"
)

// Version represents a semantic version following SemVer 2.0.0
type Version struct {
	Major      int
	Minor      int
	Patch      int
	PreRelease string
	Build      string
	Timestamp  time.Time
}

// VersionInfo holds version metadata for a model
type VersionInfo struct {
	ModelID      string    `json:"model_id"`
	Version      string    `json:"version"`
	Checksum     string    `json:"checksum,omitempty"`
	Path         string    `json:"path"`
	CreatedAt    time.Time `json:"created_at"`
	DeployedAt   time.Time `json:"deployed_at"`
	Status       string    `json:"status"` // pending, deployed, archived
	Metadata     map[string]string `json:"metadata,omitempty"`
	Author       string    `json:"author,omitempty"`
	Description  string    `json:"description,omitempty"`
}

// ModelVersioner handles model version management
type ModelVersioner struct {
	cfg     *config.Config
	logger  *logging.Logger
	storage map[string][]VersionInfo // modelID -> versions
}

// NewModelVersioner creates a new ModelVersioner instance
func NewModelVersioner(cfg *config.Config, logger *logging.Logger) *ModelVersioner {
	return &ModelVersioner{
		cfg:     cfg,
		logger  logger,
		storage: make(map[string][]VersionInfo),
	}
}

// ParseVersion parses a version string into Version struct
func ParseVersion(versionStr string) (*Version, error) {
	if versionStr == "" {
		return nil, fmt.Errorf("version string cannot be empty")
	}

	// Remove 'v' prefix if present
	versionStr = strings.TrimPrefix(versionStr, "v")

	// Regex to match SemVer pattern
	re := regexp.MustCompile(`^(\d+)\.(\d+)\.(\d+)(?:-([0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*))?(?:\+([0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*))?$`)
	matches := re.FindStringSubmatch(versionStr)

	if len(matches) == 0 {
		return nil, fmt.Errorf("invalid semantic version format: %s", versionStr)
	}

	major, _ := strconv.Atoi(matches[1])
	minor, _ := strconv.Atoi(matches[2])
	patch, _ := strconv.Atoi(matches[3])

	return &Version{
		Major:      major,
		Minor:      minor,
		Patch:      patch,
		PreRelease: matches[4],
		Build:      matches[5],
		Timestamp:  time.Now().UTC(),
	}, nil
}

// Compare compares two versions following SemVer rules
func (v *Version) Compare(other *Version) int {
	if v.Major != other.Major {
		if v.Major > other.Major {
			return 1
		}
		return -1
	}

	if v.Minor != other.Minor {
		if v.Minor > other.Minor {
			return 1
		}
		return -1
	}

	if v.Patch != other.Patch {
		if v.Patch > other.Patch {
			return 1
		}
		return -1
	}

	// Compare pre-release versions if present
	if v.PreRelease == "" && other.PreRelease != "" {
		return 1 // stable > pre-release
	}
	if v.PreRelease != "" && other.PreRelease == "" {
		return -1 // pre-release < stable
	}
	if v.PreRelease == other.PreRelease {
		return 0
	}

	// Pre-release comparison (simplified)
	vParts := strings.Split(v.PreRelease, ".")
	oParts := strings.Split(other.PreRelease, ".")

	for i := 0; i < len(vParts) && i < len(oParts); i++ {
		vNum, vErr := strconv.Atoi(vParts[i])
		oNum, oErr := strconv.Atoi(oParts[i])

		// If both are numbers, compare numerically
		if vErr == nil && oErr == nil {
			if vNum > oNum {
				return 1
			} else if vNum < oNum {
				return -1
			}
			continue
		}

		// If both are strings, compare lexically
		if vErr != nil && oErr != nil {
			if vParts[i] > oParts[i] {
				return 1
			} else if vParts[i] < oParts[i] {
				return -1
			}
			continue
		}

		// Numeric identifiers have lower precedence than alphanumeric
		if vErr == nil {
			return -1
		}
		return 1
	}

	if len(vParts) > len(oParts) {
		return 1
	} else if len(vParts) < len(oParts) {
		return -1
	}

	return 0
}

// String returns the standard string representation of the version
func (v *Version) String() string {
	version := fmt.Sprintf("%d.%d.%d", v.Major, v.Minor, v.Patch)
	if v.PreRelease != "" {
		version += "-" + v.PreRelease
	}
	if v.Build != "" {
		version += "+" + v.Build
	}
	return version
}

// GenerateNextVersion generates the next version number
// If currentVersion is empty, returns "1.0.0"
// If currentVersion is provided, increments patch version
func (mv *ModelVersioner) GenerateNextVersion(currentVersion string) (string, error) {
	if currentVersion == "" {
		return "1.0.0", nil
	}

	v, err := ParseVersion(currentVersion)
	if err != nil {
		return "", fmt.Errorf("failed to parse current version: %w", err)
	}

	// Increment patch version
	newVersion := &Version{
		Major:     v.Major,
		Minor:     v.Minor,
		Patch:     v.Patch + 1,
		Timestamp: time.Now().UTC(),
	}

	return newVersion.String(), nil
}

// RegisterVersion registers a new version for a model
func (mv *ModelVersioner) RegisterVersion(modelID, version, path, checksum string, metadata map[string]string, author, description string) (*VersionInfo, error) {
	mv.logger.Info("registering new model version", map[string]interface{}{
		"model_id": modelID,
		"version":  version,
		"path":     path,
	})

	// Validate version format
	if _, err := ParseVersion(version); err != nil {
		return nil, fmt.Errorf("invalid version format: %w", err)
	}

	// Create version info
	versionInfo := VersionInfo{
		ModelID:     modelID,
		Version:     version,
		Path:        path,
		Checksum:    checksum,
		CreatedAt:   time.Now().UTC(),
		Status:      "pending",
		Metadata:    metadata,
		Author:      author,
		Description: description,
	}

	// Add to storage
	mv.storage[modelID] = append(mv.storage[modelID], versionInfo)

	mv.logger.Info("model version registered successfully", map[string]interface{}{
		"model_id": modelID,
		"version":  version,
	})

	return &versionInfo, nil
}

// GetLatestVersion returns the latest version of a model
func (mv *ModelVersioner) GetLatestVersion(modelID string) (*VersionInfo, error) {
	versions, exists := mv.storage[modelID]
	if !exists || len(versions) == 0 {
		return nil, fmt.Errorf("no versions found for model: %s", modelID)
	}

	var latest *VersionInfo
	for i := range versions {
		if latest == nil || mv.isNewerVersion(versions[i].Version, latest.Version) {
			latest = &versions[i]
		}
	}

	return latest, nil
}

// GetVersion returns a specific version of a model
func (mv *ModelVersioner) GetVersion(modelID, version string) (*VersionInfo, error) {
	versions, exists := mv.storage[modelID]
	if !exists {
		return nil, fmt.Errorf("model not found: %s", modelID)
	}

	for _, v := range versions {
		if v.Version == version {
			return &v, nil
		}
	}

	return nil, fmt.Errorf("version not found: %s for model: %s", version, modelID)
}

// ListVersions returns all versions for a model, sorted by semantic versioning
func (mv *ModelVersioner) ListVersions(modelID string) ([]VersionInfo, error) {
	versions, exists := mv.storage[modelID]
	if !exists {
		return nil, fmt.Errorf("model not found: %s", modelID)
	}

	// Sort versions by semantic versioning
	sorted := make([]VersionInfo, len(versions))
	copy(sorted, versions)
	sort.Slice(sorted, func(i, j int) bool {
		vi, _ := ParseVersion(sorted[i].Version)
		vj, _ := ParseVersion(sorted[j].Version)
		return vi.Compare(vj) > 0
	})

	return sorted, nil
}

// UpdateVersionStatus updates the status of a model version
func (mv *ModelVersioner) UpdateVersionStatus(modelID, version, status string) error {
	versions, exists := mv.storage[modelID]
	if !exists {
		return fmt.Errorf("model not found: %s", modelID)
	}

	for i := range versions {
		if versions[i].Version == version {
			oldStatus := versions[i].Status
			versions[i].Status = status

			if status == "deployed" {
				versions[i].DeployedAt = time.Now().UTC()
			}

			mv.logger.Info("version status updated", map[string]interface{}{
				"model_id": modelID,
				"version":  version,
				"old":      oldStatus,
				"new":      status,
			})

			return nil
		}
	}

	return fmt.Errorf("version not found: %s for model: %s", version, modelID)
}

// ArchiveVersion marks a version as archived
func (mv *ModelVersioner) ArchiveVersion(modelID, version string) error {
	return mv.UpdateVersionStatus(modelID, version, "archived")
}

// DeployVersion marks a version as deployed
func (mv *ModelVersioner) DeployVersion(modelID, version string) error {
	return mv.UpdateVersionStatus(modelID, version, "deployed")
}

// isNewerVersion checks if version a is newer than version b
func (mv *ModelVersioner) isNewerVersion(a, b string) bool {
	va, err := ParseVersion(a)
	if err != nil {
		return false
	}

	vb, err := ParseVersion(b)
	if err != nil {
		return false
	}

	return va.Compare(vb) > 0
}

// MigrateVersionStorage performs any necessary migrations on version storage
// Currently a no-op but留 for future extensibility
func (mv *ModelVersioner) MigrateVersionStorage() error {
	mv.logger.Info("performing version storage migration", nil)
	// Future migration logic would go here
	return nil
}

// ValidateVersionCompatibility checks if two versions are compatible
// based on major, minor, patch rules
func (mv *ModelVersioner) ValidateVersionCompatibility(oldVer, newVer string) (bool, error) {
	oldVersion, err := ParseVersion(oldVer)
	if err != nil {
		return false, fmt.Errorf("failed to parse old version: %w", err)
	}

	newVersion, err := ParseVersion(newVer)
	if err != nil {
		return false, fmt.Errorf("failed to parse new version: %w", err)
	}

	// Major version change - potential breaking changes
	if newVersion.Major > oldVersion.Major {
		mv.logger.Warn("major version change detected - potential breaking changes", map[string]interface{}{
			"old_version": oldVer,
			"new_version": newVer,
		})
		return false, nil
	}

	// Backward compatible changes
	return true, nil
}