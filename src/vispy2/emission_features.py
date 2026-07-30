"""VisPy2-local declarations of GSP semantics this producer can emit."""

from enum import StrEnum


class EmissionFeature(StrEnum):
    """Stable, non-wire producer feature identifiers owned by VisPy2."""

    MESHVISUAL_MATERIAL_TEXTURE2D_UNLIT_V1 = (
        "vispy2.emit.meshvisual.material.texture2d_unlit.v1"
    )
    MESHVISUAL_TEXTURE_FILTER_LINEAR_V1 = (
        "vispy2.emit.meshvisual.texture_filter.linear.v1"
    )


EMISSION_FEATURES: frozenset[EmissionFeature] = frozenset(EmissionFeature)
