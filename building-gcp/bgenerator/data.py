from dataclasses import dataclass
from types import MappingProxyType


@dataclass(frozen=True)
class BuildingTypeSpec:
    identifier: str
    label: str
    description: str
    generator_profile: str
    defaults: MappingProxyType


def _defaults(**values):
    return MappingProxyType(values)


BUILDING_TYPE_ORDER = (
    "PALACE",
    "HALL",
    "TOWER",
    "CABINET",
    "GALLERY",
)

BUILDING_TYPE_SPECS = MappingProxyType(
    {
        "PALACE": BuildingTypeSpec(
            identifier="PALACE",
            label="Palace",
            description="Large formal building with broad footprint and many facade bays",
            generator_profile="symmetrical_monument",
            defaults=_defaults(
                building_width=10.0,
                building_depth=6.0,
                floors=3,
                floor_height=3.2,
                roof_style='FLAT',
                roof_height=0.45,
                roof_overhang=0.35,
                window_columns=6,
                side_window_columns=3,
                window_width=0.72,
                window_height=1.25,
                door_width=1.6,
                door_height=2.5,
                wall_color=(0.70, 0.65, 0.54, 1.0),
                roof_color=(0.28, 0.12, 0.08, 1.0),
                glass_color=(0.13, 0.28, 0.42, 0.72),
                door_color=(0.32, 0.15, 0.06, 1.0),
                trim_color=(0.86, 0.82, 0.72, 1.0),
            ),
        ),
        "HALL": BuildingTypeSpec(
            identifier="HALL",
            label="Hall",
            description="Vietnamese Ly Dynasty inspired ceremonial hall with raised platform and layered golden roofs",
            generator_profile="ly_dynasty_ceremonial_hall",
            defaults=_defaults(
                building_width=10.5,
                building_depth=5.2,
                floors=1,
                floor_height=3.2,
                roof_style='GABLE',
                roof_height=2.09,
                roof_overhang=1.89,
                window_columns=0,
                side_window_columns=0,
                window_width=0.72,
                window_height=1.1,
                door_width=1.8,
                door_height=2.4,
                platform_height=0.9,
                platform_margin=2.6,
                stair_width=2.8,
                stair_steps=7,
                side_stairs_enabled=True,
                balustrade_enabled=True,
                balustrade_height=0.36,
                balustrade_post_spacing=0.25,
                bay_count=5,
                side_bay_count=2,
                column_radius=0.09,
                column_height=1.4,
                round_pillar_offset=-0.27,
                horizontal_beam_z_offset=0.0,
                cross_beam_z_offset=0.0,
                cross_beam_length=6.16,
                main_door_height=1.0,
                lower_roof_height=0.94,
                upper_platform_height=0.3,
                upper_roof_height=1.46,
                roof_curve=0.12,
                roof_line_width=0.10,
                roof_line_height=0.10,
                roof_underside_thickness=0.01,
                roof_underside_z_offset=0.0,
                roof_tiles_enabled=True,
                roof_ying_tile_radius=0.03,
                roof_yang_tile_radius=0.10,
                roof_ying_tile_z_offset=0.03,
                roof_tile_gap=0.02,
                roof_tile_safe_distance=0.08,
                roof_tile_thickness=0.03,
                roof_tile_segment_length=0.18,
                eave_overhang=0.75,
                lower_eave_overhang=0.75,
                upper_eave_overhang=0.45,
                wall_color=(0.55, 0.55, 0.52, 1.0),
                roof_color=(1.0, 0.72, 0.08, 1.0),
                glass_color=(0.20, 0.18, 0.16, 1.0),
                door_color=(0.55, 0.03, 0.02, 1.0),
                trim_color=(0.42, 0.02, 0.01, 1.0),
            ),
        ),
        "TOWER": BuildingTypeSpec(
            identifier="TOWER",
            label="Tower",
            description="Tall narrow building with stacked windows",
            generator_profile="vertical_stack",
            defaults=_defaults(
                building_width=4.0,
                building_depth=4.0,
                floors=7,
                floor_height=2.7,
                roof_style='GABLE',
                roof_height=1.3,
                roof_overhang=0.18,
                window_columns=2,
                side_window_columns=2,
                window_width=0.55,
                window_height=0.95,
                door_width=0.95,
                door_height=2.1,
                wall_color=(0.55, 0.55, 0.52, 1.0),
                roof_color=(0.18, 0.16, 0.15, 1.0),
                glass_color=(0.10, 0.24, 0.36, 0.72),
                door_color=(0.22, 0.12, 0.07, 1.0),
                trim_color=(0.70, 0.69, 0.63, 1.0),
            ),
        ),
        "CABINET": BuildingTypeSpec(
            identifier="CABINET",
            label="Cabinet",
            description="Compact administrative building with modest footprint",
            generator_profile="compact_block",
            defaults=_defaults(
                building_width=4.8,
                building_depth=3.4,
                floors=2,
                floor_height=2.6,
                roof_style='FLAT',
                roof_height=0.28,
                roof_overhang=0.16,
                window_columns=3,
                side_window_columns=1,
                window_width=0.58,
                window_height=0.92,
                door_width=0.9,
                door_height=2.0,
                wall_color=(0.58, 0.53, 0.46, 1.0),
                roof_color=(0.22, 0.18, 0.15, 1.0),
                glass_color=(0.12, 0.27, 0.40, 0.72),
                door_color=(0.25, 0.13, 0.08, 1.0),
                trim_color=(0.74, 0.70, 0.62, 1.0),
            ),
        ),
        "GALLERY": BuildingTypeSpec(
            identifier="GALLERY",
            label="Gallery",
            description="Long low building with wide display windows",
            generator_profile="long_low",
            defaults=_defaults(
                building_width=9.0,
                building_depth=3.8,
                floors=1,
                floor_height=3.4,
                roof_style='FLAT',
                roof_height=0.32,
                roof_overhang=0.28,
                window_columns=5,
                side_window_columns=1,
                window_width=1.1,
                window_height=1.45,
                door_width=1.2,
                door_height=2.25,
                wall_color=(0.66, 0.64, 0.58, 1.0),
                roof_color=(0.20, 0.20, 0.18, 1.0),
                glass_color=(0.10, 0.28, 0.45, 0.68),
                door_color=(0.18, 0.16, 0.13, 1.0),
                trim_color=(0.82, 0.80, 0.74, 1.0),
            ),
        ),
    }
)


def building_type_items():
    return tuple(
        (identifier, BUILDING_TYPE_SPECS[identifier].label, BUILDING_TYPE_SPECS[identifier].description)
        for identifier in BUILDING_TYPE_ORDER
    )


def building_type_spec(identifier):
    return BUILDING_TYPE_SPECS.get(identifier, BUILDING_TYPE_SPECS["HALL"])
