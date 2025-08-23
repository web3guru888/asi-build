import React, { useState, useCallback } from 'react';
import { Box, TextField, Select, MenuItem, InputLabel, FormControl, Chip, Button, Stack } from '@mui/material';
import { FilterAlt as FilterIcon, Clear as ClearIcon } from '@mui/icons-material';
import { styled } from '@mui/system';

interface FilterOption {
  label: string;
  value: string;
}

interface FilterConfig {
  key: string;
  label: string;
  type: 'text' | 'select';
  options?: FilterOption[];
}

interface FilterBarProps {
  filters: FilterConfig[];
  onFilterChange: (filters: Record<string, string>) => void;
  onClear: () => void;
  initialValues?: Record<string, string>;
}

const StyledFilterBar = styled(Box)(({ theme }) => ({
  display: 'flex',
  gap: theme.spacing(2),
  padding: theme.spacing(2),
  backgroundColor: theme.palette.background.paper,
  borderBottom: `1px solid ${theme.palette.divider}`,
  flexWrap: 'wrap',
  alignItems: 'center',
}));

const FilterLabel = styled(InputLabel)(({ theme }) => ({
  fontSize: '0.875rem',
  fontWeight: 500,
  marginBottom: theme.spacing(0.5),
}));

const ActionButton = styled(Button)(({ theme }) => ({
  marginTop: '1.5rem',
  minWidth: 'auto',
  padding: theme.spacing(1),
}));

const FilterBar: React.FC<FilterBarProps> = ({
  filters,
  onFilterChange,
  onClear,
  initialValues = {},
}) => {
  const [localFilters, setLocalFilters] = useState<Record<string, string>>(initialValues);

  const handleTextChange = useCallback(
    (key: string, value: string) => {
      const updatedFilters = { ...localFilters, [key]: value };
      setLocalFilter(key, value);
      onFilterChange(updatedFilters);
    },
    [localFilters, onFilterChange]
  );

  const handleSelectChange = useCallback(
    (key: string, value: string) => {
      const updatedFilters = { ...localFilters, [key]: value };
      setLocalFilter(key, value);
      onFilterChange(updatedFilters);
    },
    [localFilters, onFilterChange]
  );

  const setLocalFilter = useCallback((key: string, value: string) => {
    setLocalFilters((prev) => ({ ...prev, [key]: value }));
  }, []);

  const handleClear = useCallback(() => {
    setLocalFilters({});
    onClear();
  }, [onClear]);

  const hasActiveFilters = Object.keys(localFilters).length > 0;

  return (
    <StyledFilterBar>
      <Stack direction="row" spacing={2} alignItems="flex-end" flexWrap="wrap" flexGrow={1}>
        {filters.map((filter) => (
          <Box key={filter.key} sx={{ minWidth: 200 }}>
            <FilterLabel htmlFor={`${filter.key}-filter`}>{filter.label}</FilterLabel>
            {filter.type === 'text' ? (
              <TextField
                id={`${filter.key}-filter`}
                size="small"
                value={localFilters[filter.key] || ''}
                onChange={(e) => handleTextChange(filter.key, e.target.value)}
                variant="outlined"
                fullWidth
                placeholder={`Enter ${filter.label.toLowerCase()}...`}
              />
            ) : (
              <FormControl fullWidth>
                <Select
                  id={`${filter.key}-filter`}
                  value={localFilters[filter.key] || ''}
                  onChange={(e) => handleSelectChange(filter.key, e.target.value as string)}
                  displayEmpty
                  size="small"
                >
                  <MenuItem value="">
                    <em>All {filter.label}</em>
                  </MenuItem>
                  {filter.options?.map((option) => (
                    <MenuItem key={option.value} value={option.value}>
                      {option.label}
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>
            )}
          </Box>
        ))}

        {(hasActiveFilters || onClear) && (
          <ActionButton
            onClick={handleClear}
            color="secondary"
            variant="outlined"
            startIcon={<ClearIcon />}
            aria-label="Clear all filters"
          >
            Clear
          </ActionButton>
        )}
      </Stack>

      {hasActiveFilters && (
        <Stack direction="row" spacing={1} flexWrap="wrap" sx={{ mt: 2, flexGrow: { xs: 1, sm: 0 } }}>
          {Object.entries(localFilters).map(([key, value]) => {
            const filterConfig = filters.find((f) => f.key === key);
            if (!value || !filterConfig) return null;

            return (
              <Chip
                key={key}
                label={`${filterConfig.label}: ${value}`}
                onDelete={() => {
                  const updatedFilters = { ...localFilters };
                  delete updatedFilters[key];
                  setLocalFilters(updatedFilters);
                  onFilterChange(updatedFilters);
                }}
                size="small"
                color="primary"
                variant="outlined"
              />
            );
          })}
        </Stack>
      )}
    </StyledFilterBar>
  );
};

export default FilterBar;