from __future__ import annotations


LEGACY_DYNAMIC_SCENARIOS = [
    {
        "id": "S1",
        "label": "S1 – Pre-fire Baseline",
        "description": "1985 land-use baseline with transient climate forcing.",
        "is_change": False,
        "variables": [
            "streamflow",
            "baseflow",
            "return",
            "trans",
            "evap",
            "lai",
            "gpsn",
            "plantc",
            "et",
            "plant_c",
            "litter_c",
            "soil_c",
        ],
        "year_range": [1985, 2024],
        "geometry_revision": "legacy-1985",
    },
    {
        "id": "S2",
        "label": "S2 – Post-fire Land Cover",
        "description": "2021 post-fire land cover with transient climate forcing.",
        "is_change": False,
        "variables": [
            "streamflow",
            "baseflow",
            "return",
            "trans",
            "evap",
            "lai",
            "gpsn",
            "plantc",
            "et",
            "plant_c",
            "litter_c",
            "soil_c",
        ],
        "year_range": [1985, 2024],
        "geometry_revision": "legacy-2021",
    },
    {
        "id": "S4b",
        "label": "S4b – Post-fire Regrowth",
        "description": "Observed fire effects and post-fire regrowth with transient climate.",
        "is_change": False,
        "variables": [
            "streamflow",
            "baseflow",
            "return",
            "trans",
            "evap",
            "lai",
            "gpsn",
            "plantc",
            "et",
            "plant_c",
            "litter_c",
            "soil_c",
        ],
        "year_range": [1985, 2024],
        "geometry_revision": "legacy-2021",
    },
]

LEGACY_DYNAMIC_VARIABLES = [
    {"id": "streamflow", "label": "Streamflow", "units": "mm/day", "spatial_scales": ["hillslope"]},
    {"id": "baseflow", "label": "Baseflow", "units": "mm/day", "spatial_scales": ["hillslope"]},
    {"id": "return", "label": "Return Flow", "units": "mm/day", "spatial_scales": ["hillslope"]},
    {"id": "trans", "label": "Transpiration", "units": "mm/day", "spatial_scales": ["hillslope"]},
    {"id": "evap", "label": "Evaporation", "units": "mm/day", "spatial_scales": ["hillslope"]},
    {"id": "lai", "label": "LAI", "units": "m²/m²", "spatial_scales": ["hillslope", "patch"]},
    {"id": "gpsn", "label": "GPP", "units": "gC/m²/day", "spatial_scales": ["hillslope"]},
    {"id": "plantc", "label": "Plant Biomass", "units": "kgC/m²", "spatial_scales": ["hillslope"]},
    {"id": "et", "label": "Evapotranspiration", "units": "mm/yr", "spatial_scales": ["patch"]},
    {"id": "plant_c", "label": "Plant Carbon", "units": "kgC/m²", "spatial_scales": ["patch"]},
    {"id": "litter_c", "label": "Litter Carbon", "units": "kgC/m²", "spatial_scales": ["patch"]},
    {"id": "soil_c", "label": "Soil Carbon", "units": "kgC/m²", "spatial_scales": ["patch"]},
]

LEGACY_HILLSLOPE_GROW_VARIABLES = {"lai", "gpsn", "plantc"}
LEGACY_PATCH_GROW_VARIABLES = {"plant_c", "litter_c", "soil_c"}


def legacy_parquet_path(
    scenario: str,
    spatial_scale: str,
    variable: str,
    query_kind: str,
) -> tuple[str, str]:
    if scenario not in {"S1", "S2", "S4b"}:
        raise KeyError("unknown legacy RHESSys scenario")
    if spatial_scale not in {"hillslope", "patch"}:
        raise KeyError("unknown legacy RHESSys scale")
    supported_variables = {
        item["id"]
        for item in LEGACY_DYNAMIC_VARIABLES
        if spatial_scale in item["spatial_scales"]
    }
    if variable not in supported_variables:
        raise KeyError("unsupported legacy RHESSys variable")
    grow = variable in (
        LEGACY_HILLSLOPE_GROW_VARIABLES
        if spatial_scale == "hillslope"
        else LEGACY_PATCH_GROW_VARIABLES
    )
    prefix = "grow_" if grow else ""
    if query_kind == "time-series" and spatial_scale == "hillslope":
        filename = f"{prefix}basin.daily.parquet"
        return f"rhessys/scenarios/{scenario}/{filename}", "basinID"
    filename = (
        f"{prefix}hillslope.daily.parquet"
        if spatial_scale == "hillslope"
        else f"{prefix}patch.yearly.parquet"
    )
    spatial_id = "basinID" if grow and spatial_scale == "hillslope" else (
        "hillID" if spatial_scale == "hillslope" else "patchID"
    )
    return f"rhessys/scenarios/{scenario}/{filename}", spatial_id


def legacy_geometry_path(scale: str, scenario: str | None) -> tuple[str, str]:
    if scale == "hillslope":
        return (
            "rhessys/spatial_inputs_and_climates/masked_tol_1000cleaned_hillslop.geojson",
            "legacy-hillslope",
        )
    if scale == "patch":
        revision = "2021" if scenario in {"S2", "S4b"} else "1985"
        return (
            f"rhessys/spatial_inputs_and_climates/masked_daymet_patchID_{revision}.geojson",
            f"legacy-{revision}",
        )
    raise KeyError("unknown legacy RHESSys geometry scale")
