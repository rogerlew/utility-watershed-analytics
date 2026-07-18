import { useCallback, useMemo } from "react";
import { useWatershed } from "../../../contexts/WatershedContext";
import {
  getLayerParams,
  type RhessysOutputParams,
} from "../../../layers/types";

import { useStyles } from "../watershedStyles";
import Typography from "@mui/material/Typography";
import Tooltip from "@mui/material/Tooltip";
import FormControl from "@mui/material/FormControl";
import InputLabel from "@mui/material/InputLabel";
import Select from "@mui/material/Select";
import MenuItem from "@mui/material/MenuItem";
import ToggleButton from "@mui/material/ToggleButton";
import ToggleButtonGroup from "@mui/material/ToggleButtonGroup";
import InfoOutlinedIcon from "@mui/icons-material/InfoOutlined";
import PanelStatus from "../../PanelStatus";
import type {
  RhessysOutputScenario,
  RhessysOutputVariable,
} from "../../../api/types/rhessys";

export function RhessysOutputsControls({
  scenarios,
  variables,
  isLoading,
  hasRasterData,
  hasChoroplethData,
}: {
  scenarios: RhessysOutputScenario[];
  variables: RhessysOutputVariable[];
  isLoading: boolean;
  hasRasterData: boolean;
  hasChoroplethData: boolean;
}) {
  const { classes } = useStyles();
  const {
    layerDesired,
    dispatchLayerAction,
    enableLayerWithParams,
    effective,
  } = useWatershed();

  const params = getLayerParams(layerDesired, "rhessysOutputs");
  const selectedScenario = params.scenario ?? null;
  const selectedVariable = params.variable ?? null;
  const selectedScenarioMeta = scenarios.find(
    (scenario) => scenario.id === selectedScenario,
  );
  const selectedMode = params.mode ?? (hasRasterData ? "raster" : "choropleth");
  const selectedSpatialScale = (params.spatialScale ?? "hillslope") as
    | "hillslope"
    | "patch";
  const [minimumYear, maximumYear] = selectedScenarioMeta?.year_range ?? [
    2000, 2000,
  ];
  const selectedYear =
    params.year != null &&
    params.year >= minimumYear &&
    params.year <= maximumYear
      ? params.year
      : minimumYear;
  const layerEnabled = effective.rhessysOutputs.enabled;

  const availableVariables = useMemo(() => {
    const meta = scenarios.find((s) => s.id === selectedScenario);
    return meta
      ? variables.filter((v) => meta.variables.includes(v.id))
      : variables;
  }, [scenarios, variables, selectedScenario]);

  const choroplethVariables = useMemo(() => {
    const scenarioVariables = selectedScenarioMeta?.variables;
    return variables.filter(
      (variable) =>
        (!scenarioVariables || scenarioVariables.includes(variable.id)) &&
        variable.spatial_scales?.includes(selectedSpatialScale),
    );
  }, [selectedScenarioMeta, selectedSpatialScale, variables]);
  const years = useMemo(() => {
    return Array.from(
      { length: maximumYear - minimumYear + 1 },
      (_, index) => minimumYear + index,
    );
  }, [maximumYear, minimumYear]);

  const currentParams = useMemo(
    () => ({
      scenario: selectedScenario,
      variable: selectedVariable,
      mode: selectedMode,
      spatialScale: selectedSpatialScale,
      year: selectedYear,
    }),
    [
      selectedScenario,
      selectedVariable,
      selectedMode,
      selectedSpatialScale,
      selectedYear,
    ],
  );

  const updateParams = useCallback(
    (overrides: Partial<RhessysOutputParams>) =>
      enableLayerWithParams("rhessysOutputs", {
        ...currentParams,
        ...overrides,
      }),
    [enableLayerWithParams, currentParams],
  );

  const turnOff = useCallback(
    () =>
      dispatchLayerAction({ type: "TOGGLE", id: "rhessysOutputs", on: false }),
    [dispatchLayerAction],
  );

  const handleSpatialScaleChange = useCallback(
    (
      _: React.MouseEvent<HTMLElement>,
      newScale: "hillslope" | "patch" | null,
    ) => {
      if (!newScale) return;
      const vars = variables.filter(
        (variable) =>
          (!selectedScenarioMeta ||
            selectedScenarioMeta.variables.includes(variable.id)) &&
          variable.spatial_scales?.includes(newScale),
      );
      const nextVariable = vars.some((v) => v.id === selectedVariable)
        ? selectedVariable
        : (vars[0]?.id ?? null);
      const nextParams: Partial<RhessysOutputParams> = {
        spatialScale: newScale,
        variable: nextVariable,
        mode: "choropleth",
      };
      if (layerEnabled) {
        updateParams(nextParams);
      } else {
        for (const [key, value] of Object.entries(nextParams)) {
          dispatchLayerAction({
            type: "SET_PARAM",
            id: "rhessysOutputs",
            key,
            value,
          });
        }
      }
    },
    [
      updateParams,
      dispatchLayerAction,
      layerEnabled,
      selectedVariable,
      selectedScenarioMeta,
      variables,
    ],
  );

  if (isLoading)
    return (
      <PanelStatus
        status="loading"
        size="sm"
        message="Checking for output data…"
      />
    );
  if (!hasRasterData && !hasChoroplethData) return null;

  // Pre-computed raster maps (Victoria + Mill Creek)
  if (hasRasterData && selectedMode !== "choropleth") {
    const rasterDescription = selectedScenarioMeta?.description;
    return (
      <>
        <FormControl
          fullWidth
          size="small"
          className={classes.rhessysOutputFormControl}
        >
          <InputLabel
            id="rhessys-outputs-scenario-label"
            className={classes.rhessysLabel}
          >
            Scenario
          </InputLabel>
          <Select
            labelId="rhessys-outputs-scenario-label"
            id="rhessys-outputs-scenario-select"
            value={layerEnabled && selectedScenario ? selectedScenario : "none"}
            label="Scenario"
            onChange={(e) => {
              const value = e.target.value;
              if (value === "none") return turnOff();
              const scenario = scenarios.find((item) => item.id === value);
              const nextVariables = variables.filter((variable) =>
                scenario?.variables.includes(variable.id),
              );
              updateParams({
                scenario: value,
                variable: nextVariables.some(
                  (variable) => variable.id === selectedVariable,
                )
                  ? selectedVariable
                  : (nextVariables[0]?.id ?? null),
                mode: "raster",
                spatialScale: null,
                year: null,
              });
            }}
            className={classes.rhessysSelect}
            MenuProps={{
              PaperProps: { className: classes.rhessysOutputSelectPaper },
            }}
          >
            <MenuItem value="none">None</MenuItem>
            {scenarios.map((s) => (
              <MenuItem key={s.id} value={s.id}>
                {s.label}
              </MenuItem>
            ))}
          </Select>
        </FormControl>

        {layerEnabled && selectedScenario && rasterDescription && (
          <Tooltip
            title={rasterDescription}
            placement="top"
            arrow
            classes={{
              tooltip: classes.tooltipBubble,
              arrow: classes.tooltipArrow,
            }}
          >
            <Typography
              className={classes.scenarioInfo}
              tabIndex={0}
              role="button"
              aria-label="About this scenario"
            >
              <InfoOutlinedIcon fontSize="inherit" />
              About this scenario
            </Typography>
          </Tooltip>
        )}

        {layerEnabled && selectedScenario && (
          <FormControl
            fullWidth
            size="small"
            className={classes.rhessysOutputFormControl}
          >
            <InputLabel
              id="rhessys-outputs-variable-label"
              className={classes.rhessysLabel}
            >
              Variable
            </InputLabel>
            <Select
              labelId="rhessys-outputs-variable-label"
              id="rhessys-outputs-variable-select"
              value={selectedVariable || ""}
              label="Variable"
              onChange={(e) => updateParams({ variable: e.target.value })}
              className={classes.rhessysSelect}
              MenuProps={{
                PaperProps: { className: classes.rhessysOutputSelectPaper },
              }}
            >
              {availableVariables.map((v) => (
                <MenuItem key={v.id} value={v.id}>
                  {v.label} ({v.units})
                </MenuItem>
              ))}
            </Select>
          </FormControl>
        )}
      </>
    );
  }

  // Dynamic choropleth
  return (
    <>
      <FormControl
        fullWidth
        size="small"
        className={classes.rhessysOutputFormControl}
      >
        <InputLabel
          id="rhessys-choropleth-scenario-label"
          className={classes.rhessysLabel}
        >
          Scenario
        </InputLabel>
        <Select
          labelId="rhessys-choropleth-scenario-label"
          id="rhessys-choropleth-scenario-select"
          value={layerEnabled && selectedScenario ? selectedScenario : "none"}
          label="Scenario"
          onChange={(e) => {
            const value = e.target.value;
            if (value === "none") return turnOff();
            const scenario = scenarios.find((item) => item.id === value);
            const nextVariables = variables.filter(
              (variable) =>
                scenario?.variables.includes(variable.id) &&
                variable.spatial_scales?.includes(selectedSpatialScale),
            );
            updateParams({
              scenario: value,
              variable: nextVariables.some(
                (variable) => variable.id === selectedVariable,
              )
                ? selectedVariable
                : (nextVariables[0]?.id ?? null),
              year: scenario?.year_range?.[0] ?? minimumYear,
              mode: "choropleth",
            });
          }}
          className={classes.rhessysSelect}
          MenuProps={{
            PaperProps: { className: classes.rhessysOutputSelectPaper },
          }}
        >
          <MenuItem value="none">None</MenuItem>
          {scenarios.map((s) => (
            <MenuItem key={s.id} value={s.id}>
              {s.label}
            </MenuItem>
          ))}
        </Select>
      </FormControl>

      {layerEnabled &&
        selectedScenario &&
        selectedScenarioMeta?.description && (
          <Tooltip
            title={selectedScenarioMeta.description}
            placement="top"
            arrow
            classes={{
              tooltip: classes.tooltipBubble,
              arrow: classes.tooltipArrow,
            }}
          >
            <Typography
              className={classes.scenarioInfo}
              tabIndex={0}
              role="button"
              aria-label="About this scenario"
            >
              <InfoOutlinedIcon fontSize="inherit" />
              About this scenario
            </Typography>
          </Tooltip>
        )}

      {layerEnabled && selectedScenario && (
        <>
          <FormControl
            fullWidth
            size="small"
            className={classes.rhessysOutputFormControl}
          >
            <InputLabel
              id="rhessys-choropleth-variable-label"
              className={classes.rhessysLabel}
            >
              Variable
            </InputLabel>
            <Select
              labelId="rhessys-choropleth-variable-label"
              id="rhessys-choropleth-variable-select"
              value={selectedVariable || ""}
              label="Variable"
              onChange={(e) =>
                updateParams({ variable: e.target.value, mode: "choropleth" })
              }
              className={classes.rhessysSelect}
              MenuProps={{
                PaperProps: { className: classes.rhessysOutputSelectPaper },
              }}
            >
              {choroplethVariables.map((v) => (
                <MenuItem key={v.id} value={v.id}>
                  {v.label} ({v.units})
                </MenuItem>
              ))}
            </Select>
          </FormControl>

          <FormControl
            fullWidth
            size="small"
            className={classes.rhessysOutputFormControl}
          >
            <InputLabel
              id="rhessys-choropleth-year-label"
              className={classes.rhessysLabel}
            >
              Year
            </InputLabel>
            <Select
              labelId="rhessys-choropleth-year-label"
              id="rhessys-choropleth-year-select"
              value={String(selectedYear)}
              label="Year"
              onChange={(e) =>
                updateParams({
                  year: Number(e.target.value),
                  mode: "choropleth",
                })
              }
              className={classes.rhessysSelect}
              MenuProps={{
                PaperProps: { className: classes.rhessysOutputSelectPaper },
              }}
            >
              {years.map((y) => (
                <MenuItem key={y} value={String(y)}>
                  {y}
                </MenuItem>
              ))}
            </Select>
          </FormControl>

          <Tooltip
            title="Water fluxes and productivities are sensitive to climate variability — selecting different years lets you explore that range rather than relying on a single year."
            placement="top"
            arrow
            classes={{
              tooltip: classes.tooltipBubble,
              arrow: classes.tooltipArrow,
            }}
          >
            <Typography
              className={classes.scenarioInfo}
              tabIndex={0}
              role="button"
              aria-label="Why select a year?"
            >
              <InfoOutlinedIcon fontSize="inherit" />
              Why select a year?
            </Typography>
          </Tooltip>

          <ToggleButtonGroup
            value={selectedSpatialScale}
            exclusive
            onChange={handleSpatialScaleChange}
            size="small"
            fullWidth
            className={classes.toggleGroup}
          >
            <ToggleButton value="hillslope">Hillslope</ToggleButton>
            <ToggleButton value="patch">Patch</ToggleButton>
          </ToggleButtonGroup>
        </>
      )}
    </>
  );
}
