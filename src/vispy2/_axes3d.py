"""Semantic three-dimensional axes."""

from __future__ import annotations

import math
from dataclasses import dataclass, field, replace
from typing import TYPE_CHECKING, Any

import numpy as np
import numpy.typing as npt
from gsp.protocol import (
    AxisGuide,
    Camera3D,
    ClipScope,
    ColorbarGuide,
    CoordinateSpace,
    DirectionalLight3D,
    FontRole,
    MeshColorMode,
    MeshNormalGeneration,
    MeshNormalMode,
    MeshShading,
    MeshUVMode,
    MeshVisual,
    Orbit3DPayload,
    OrthographicProjection3D,
    Pan3DPayload,
    Panel,
    PanelTextGuide,
    PanelTextRole,
    PerspectiveProjection3D,
    PixelVisual,
    PrimitiveTopology,
    PrimitiveVisual,
    Projection3D,
    SphereVisual,
    TextAnchorX,
    TextAnchorY,
    Texture2D,
    TextureFilter,
    TextVisual,
    VectorAnchor,
    VectorCap,
    VectorVisual,
    View3D,
    VisualAttachment,
    VisualTransformBinding,
    Zoom3DPayload,
    orbit_view3d,
    pan_view3d,
    zoom_view3d,
)

from ._camera_fit import _axes3d_data_bounds, _fit_orthographic_camera, _fit_perspective_camera
from ._inputs import (
    _angles,
    _colors,
    _coordinate_space,
    _faces,
    _float3,
    _font_role,
    _mesh_color,
    _mesh_color_mode,
    _mesh_normal_generation,
    _mesh_normal_mode,
    _mesh_normals,
    _mesh_shading,
    _mesh_uvs,
    _positions,
    _positions3d,
    _positive_values,
    _primitive_indices,
    _primitive_positions,
    _primitive_topology,
    _protocol_float3,
    _radii,
    _sizes,
    _text_anchor_x,
    _text_anchor_y,
    _text_rgba,
    _text_values,
    _texture_filter,
    _texture_id,
    _vector_anchor,
    _vector_cap,
    _vector_components,
    _visual_id,
)

if TYPE_CHECKING:
    from ._figure import Figure


@dataclass(slots=True)
class Axes3D:
    """Backend-neutral producer for one static GSP View3D."""

    figure: Figure
    visuals: list[
        MeshVisual | PixelVisual | SphereVisual | VectorVisual | PrimitiveVisual | TextVisual
    ] = field(default_factory=list)
    panel: Panel = field(init=False)
    view: View3D = field(init=False)
    attachments: list[VisualAttachment] = field(default_factory=list)
    axis_guides: list[AxisGuide] = field(default_factory=list)
    panel_text_guides: list[PanelTextGuide] = field(default_factory=list)
    colorbar_guides: list[ColorbarGuide] = field(default_factory=list)
    _home_view: View3D = field(init=False, repr=False)

    def __post_init__(self) -> None:
        index = len(self.figure.axes) + 1
        panel_id = f"panel:{index}"
        self.panel = Panel(id=panel_id)
        self.view = View3D(
            id=f"view:{index}",
            panel_id=panel_id,
            camera=Camera3D(
                eye=(3.0, 3.0, 3.0),
                target=(0.0, 0.0, 0.0),
                up=(0.0, 0.0, 1.0),
            ),
            projection=PerspectiveProjection3D(
                fov_y_degrees=45.0,
                near_far=(0.1, 1000.0),
            ),
        )
        self._home_view = self.view

    def _attach(self, visual_id: str) -> None:
        visual = next(visual for visual in reversed(self.visuals) if visual.id == visual_id)
        self.attachments.append(
            VisualAttachment(
                visual_id=visual_id,
                panel_id=self.panel.id,
                view_id=(self.view.id if visual.coordinate_space is CoordinateSpace.DATA else None),
                clip_scope=ClipScope.PLOT,
            )
        )

    def set_camera(
        self,
        *,
        eye: npt.ArrayLike,
        target: npt.ArrayLike,
        up: npt.ArrayLike,
    ) -> Camera3D:
        """Replace the semantic camera and increment the View3D revision."""
        camera = Camera3D(
            eye=_float3(eye, field_name="eye"),
            target=_float3(target, field_name="target"),
            up=_float3(up, field_name="up"),
        )
        self.view = replace(
            self.view,
            camera=camera,
            revision=self.view.revision + 1,
        )
        return camera

    def get_camera(self) -> Camera3D:
        """Return the current semantic camera."""
        return self.view.camera

    def set_perspective(
        self,
        *,
        fov_y_degrees: float = 45.0,
        near: float = 0.1,
        far: float = 1000.0,
        aspect_ratio: float | None = None,
    ) -> PerspectiveProjection3D:
        """Set a perspective projection and increment the View3D revision."""
        projection = PerspectiveProjection3D(
            fov_y_degrees=float(fov_y_degrees),
            near_far=(float(near), float(far)),
            aspect_ratio=None if aspect_ratio is None else float(aspect_ratio),
        )
        self.view = replace(
            self.view,
            projection=projection,
            revision=self.view.revision + 1,
        )
        return projection

    def set_orthographic(
        self,
        *,
        xlim: tuple[float, float] = (-1.0, 1.0),
        ylim: tuple[float, float] = (-1.0, 1.0),
        near: float = 0.0,
        far: float = 1000.0,
    ) -> OrthographicProjection3D:
        """Set an orthographic projection and increment the View3D revision."""
        projection = OrthographicProjection3D(
            xlim=(float(xlim[0]), float(xlim[1])),
            ylim=(float(ylim[0]), float(ylim[1])),
            near_far=(float(near), float(far)),
        )
        self.view = replace(
            self.view,
            projection=projection,
            revision=self.view.revision + 1,
        )
        return projection

    def get_projection(self) -> Projection3D:
        """Return the current semantic projection."""
        return self.view.projection

    def set_lighting(
        self,
        *,
        ambient_light_intensity: float,
        direction_to_light: npt.ArrayLike | None,
        directional_light_intensity: float = 1.0,
    ) -> View3D:
        """Set the accepted ambient and optional directional View3D lighting."""
        directional_light = (
            None
            if direction_to_light is None
            else DirectionalLight3D(
                direction_to_light=_protocol_float3(direction_to_light),
                intensity=float(directional_light_intensity),
            )
        )
        self.view = replace(
            self.view,
            ambient_light_intensity=float(ambient_light_intensity),
            directional_light=directional_light,
            revision=self.view.revision + 1,
        )
        return self.view

    def orbit(self, *, yaw_radians: float, pitch_radians: float) -> View3D:
        """Orbit with the accepted GSP reducer."""
        self.view = orbit_view3d(
            self.view,
            Orbit3DPayload(
                delta_yaw_radians=float(yaw_radians),
                delta_pitch_radians=float(pitch_radians),
            ),
        )
        return self.view

    def pan(self, *, right: float, up: float) -> View3D:
        """Pan with the accepted GSP reducer."""
        self.view = pan_view3d(
            self.view,
            Pan3DPayload(
                delta_view_right=float(right),
                delta_view_up=float(up),
            ),
        )
        return self.view

    def zoom(
        self,
        scale: float,
        *,
        anchor_ndc: tuple[float, float] | None = None,
    ) -> View3D:
        """Zoom with the accepted GSP reducer."""
        anchor = None if anchor_ndc is None else (float(anchor_ndc[0]), float(anchor_ndc[1]))
        self.view = zoom_view3d(
            self.view,
            Zoom3DPayload(
                scale=float(scale),
                anchor_plot_ndc_xy=anchor,
            ),
        )
        return self.view

    def reset_camera(self) -> View3D:
        """Restore the camera and projection from axes construction."""
        self.view = replace(
            self.view,
            camera=self._home_view.camera,
            projection=self._home_view.projection,
            revision=self.view.revision + 1,
        )
        return self.view

    def fit_camera(self, *, margin: float = 1.1) -> View3D:
        """Fit the current camera/projection to finite DATA-space 3D bounds."""
        resolved_margin = float(margin)
        if not math.isfinite(resolved_margin) or resolved_margin < 1.0:
            raise ValueError("camera fit margin must be finite and at least 1")
        bounds = _axes3d_data_bounds(self.visuals)
        camera: Camera3D
        projection: Projection3D
        if isinstance(self.view.projection, PerspectiveProjection3D):
            camera, projection = _fit_perspective_camera(
                self.view,
                bounds,
                margin=resolved_margin,
            )
        else:
            camera, projection = _fit_orthographic_camera(
                self.view,
                bounds,
                margin=resolved_margin,
            )
        self.view = replace(
            self.view,
            camera=camera,
            projection=projection,
            revision=self.view.revision + 1,
        )
        return self.view

    def set_title(self, text: str | None) -> str | None:
        """Set or clear the semantic panel title."""
        self.panel_text_guides = [
            guide for guide in self.panel_text_guides if guide.role != PanelTextRole.TITLE
        ]
        if text:
            self.panel_text_guides.append(
                PanelTextGuide(
                    id=f"guide:title-{self._index}",
                    panel_id=self.panel.id,
                    role=PanelTextRole.TITLE,
                    text=text,
                )
            )
        return text

    def get_title(self) -> str | None:
        """Return the semantic panel title, if any."""
        for guide in self.panel_text_guides:
            if guide.role == PanelTextRole.TITLE:
                return guide.text
        return None

    def mesh(
        self,
        positions: npt.ArrayLike,
        faces: npt.ArrayLike,
        *,
        color: npt.ArrayLike,
        color_mode: str | MeshColorMode | None = None,
        coordinate_space: str | CoordinateSpace = CoordinateSpace.DATA,
        shading: str | MeshShading = MeshShading.UNLIT_RGBA,
        normal_mode: str | MeshNormalMode | None = None,
        normals: npt.ArrayLike | None = None,
        normal_generation: str | MeshNormalGeneration = MeshNormalGeneration.NONE,
        order: float = 0.0,
        transform: npt.ArrayLike | VisualTransformBinding | None = None,
        texture: npt.ArrayLike | None = None,
        uvs: npt.ArrayLike | None = None,
        texture_filter: str | TextureFilter = TextureFilter.NEAREST,
        id: str | None = None,
    ) -> MeshVisual:
        """Create a 3D protocol mesh attached to this View3D."""
        position_array = _positions(positions, None)
        if position_array.shape[1] != 3:
            raise ValueError("Axes3D.mesh() positions must have shape (N, 3)")
        if transform is not None:
            raise ValueError("Axes3D.mesh() transforms are not supported in this static 3D slice")
        face_array = _faces(faces)
        texture_resource = self._mesh_texture2d_resource(texture, uvs)
        mesh_shading = _mesh_shading(shading)
        mesh_uvs = None if texture_resource is None else _mesh_uvs(uvs, position_array.shape[0])
        if texture_resource is not None and mesh_shading is not MeshShading.UNLIT_RGBA:
            raise ValueError("texture2d_unlit does not accept explicit mesh shading")
        visual = MeshVisual(
            id=id or _visual_id("mesh"),
            positions=position_array,
            faces=face_array,
            coordinate_space=_coordinate_space(coordinate_space),
            color=_mesh_color(color),
            color_mode=_mesh_color_mode(color_mode),
            shading=(MeshShading.TEXTURE2D_UNLIT if texture_resource is not None else mesh_shading),
            normal_mode=_mesh_normal_mode(normal_mode),
            normals=_mesh_normals(normals),
            normal_generation=_mesh_normal_generation(normal_generation),
            texture2d_id=None if texture_resource is None else texture_resource.id,
            uv_mode=MeshUVMode.NONE if texture_resource is None else MeshUVMode.VERTEX,
            uvs=mesh_uvs,
            order=float(order),
            transform=None,
            texture_filter=_texture_filter(texture_filter),
        )
        if texture_resource is not None:
            self.figure.texture2d_resources.append(texture_resource)
        self.visuals.append(visual)
        self._attach(visual.id)
        return visual

    def pixels(
        self,
        x: npt.ArrayLike,
        y: npt.ArrayLike | None = None,
        z: npt.ArrayLike | None = None,
        *,
        color: npt.ArrayLike | None = None,
        size: npt.ArrayLike | float = 1.0,
        id: str | None = None,
    ) -> PixelVisual:
        """Create projected square pixels anchored in 3D DATA space."""
        positions = _positions3d(x, y, z)
        visual = PixelVisual(
            id=id or _visual_id("pixels"),
            positions=positions,
            colors=_colors(color, positions.shape[0]),
            pixel_size_px=_sizes(size, positions.shape[0]),
            coordinate_space=CoordinateSpace.DATA,
        )
        self.visuals.append(visual)
        self._attach(visual.id)
        return visual

    def text(
        self,
        x: npt.ArrayLike,
        y: npt.ArrayLike | None,
        z: npt.ArrayLike | None,
        texts: str | tuple[str, ...] | list[str],
        *,
        color: npt.ArrayLike | None = None,
        font_size_px: npt.ArrayLike | float = 13.0,
        font_role: str | FontRole = FontRole.DEFAULT,
        anchor_x: str
        | TextAnchorX
        | tuple[str | TextAnchorX, ...]
        | list[str | TextAnchorX] = TextAnchorX.LEFT,
        anchor_y: str
        | TextAnchorY
        | tuple[str | TextAnchorY, ...]
        | list[str | TextAnchorY] = TextAnchorY.BASELINE,
        rotation_rad: npt.ArrayLike | float = 0.0,
        z_order: int = 0,
        id: str | None = None,
    ) -> TextVisual:
        """Create screen-facing billboard labels anchored in 3D DATA space."""
        positions = _positions3d(x, y, z)
        visual = TextVisual(
            id=id or _visual_id("text"),
            texts=_text_values(texts, positions.shape[0]),
            positions=positions,
            coordinate_space=CoordinateSpace.DATA,
            rgba=_text_rgba(color, positions.shape[0]),
            font_size_px=_positive_values(
                font_size_px, positions.shape[0], field_name="font_size_px"
            ),
            font_role=_font_role(font_role),
            anchor_x=_text_anchor_x(anchor_x, positions.shape[0]),
            anchor_y=_text_anchor_y(anchor_y, positions.shape[0]),
            rotation_rad=_angles(rotation_rad, positions.shape[0]),
            z_order=int(z_order),
        )
        self.visuals.append(visual)
        self._attach(visual.id)
        return visual

    def spheres(
        self,
        x: npt.ArrayLike,
        y: npt.ArrayLike,
        z: npt.ArrayLike,
        *,
        radius: npt.ArrayLike | float,
        color: npt.ArrayLike,
        id: str | None = None,
    ) -> SphereVisual:
        """Create DATA-space spheres with scalar or per-sphere radii and RGBA colors."""
        positions = _positions3d(x, y, z)
        visual = SphereVisual(
            id=id or _visual_id("spheres"),
            positions=positions,
            radii=_radii(radius, positions.shape[0]),
            colors=_colors(color, positions.shape[0]),
        )
        self.visuals.append(visual)
        self._attach(visual.id)
        return visual

    def vectors(
        self,
        x: npt.ArrayLike,
        y: npt.ArrayLike,
        z: npt.ArrayLike,
        u: npt.ArrayLike,
        v: npt.ArrayLike,
        w: npt.ArrayLike,
        *,
        color: npt.ArrayLike | None = None,
        width: npt.ArrayLike | float = 1.0,
        scale: float = 1.0,
        anchor: str | VectorAnchor = VectorAnchor.TAIL,
        start_cap: str | VectorCap = VectorCap.BUTT,
        end_cap: str | VectorCap = VectorCap.TRIANGLE_OUT,
        id: str | None = None,
    ) -> VectorVisual:
        """Create straight 3D DATA-space vectors from anchors and displacements."""
        positions = _positions3d(x, y, z)
        displacements = _vector_components((u, v, w), dimensions=3)
        if positions.shape != displacements.shape:
            raise ValueError("x/y/z anchors and u/v/w vectors must have the same length")
        visual = VectorVisual(
            id=id or _visual_id("vectors"),
            positions=positions,
            vectors=displacements,
            colors=_colors(color, positions.shape[0]),
            widths_px=_sizes(width, positions.shape[0]),
            scale=float(scale),
            anchor=_vector_anchor(anchor),
            start_cap=_vector_cap(start_cap),
            end_cap=_vector_cap(end_cap),
        )
        self.visuals.append(visual)
        self._attach(visual.id)
        return visual

    def primitives(
        self,
        positions: npt.ArrayLike,
        *,
        topology: str | PrimitiveTopology,
        color: npt.ArrayLike | None = None,
        indices: npt.ArrayLike | None = None,
        id: str | None = None,
    ) -> PrimitiveVisual:
        """Create bounded point, line, or triangle geometry in 3D DATA space."""
        vertices = _primitive_positions(positions, dimensions=3)
        visual = PrimitiveVisual(
            id=id or _visual_id("primitives"),
            topology=_primitive_topology(topology),
            positions=vertices,
            colors=_colors(color, vertices.shape[0]),
            indices=_primitive_indices(indices),
            coordinate_space=CoordinateSpace.DATA,
        )
        self.visuals.append(visual)
        self._attach(visual.id)
        return visual

    def quiver(
        self,
        x: npt.ArrayLike,
        y: npt.ArrayLike,
        z: npt.ArrayLike,
        u: npt.ArrayLike,
        v: npt.ArrayLike,
        w: npt.ArrayLike,
        **kwargs: Any,
    ) -> VectorVisual:
        """Thin 3D alias for :meth:`vectors`."""
        return self.vectors(x, y, z, u, v, w, **kwargs)

    def _mesh_texture2d_resource(
        self, texture: npt.ArrayLike | None, uvs: npt.ArrayLike | None
    ) -> Texture2D | None:
        if texture is None and uvs is None:
            return None
        if texture is None or uvs is None:
            raise ValueError("texture and uvs must be supplied together")
        image = np.asarray(texture)
        if image.dtype != np.dtype(np.uint8):
            raise TypeError("texture2d_invalid_resource: texture must have dtype uint8")
        return Texture2D(id=_texture_id("mesh"), image=image)

    @property
    def _index(self) -> int:
        return int(self.panel.id.rsplit(":", maxsplit=1)[1])
