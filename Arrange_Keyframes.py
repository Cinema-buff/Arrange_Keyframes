bl_info = {
    "name": "Arrange Keyframes",
    "author": "Claude",
    "version": (1, 0, 0),
    "blender": (2, 80, 0),
    "location": "Dope Sheet / Graph Editor > Header (Arrange button) and Key menu",
    "description": "Evenly spaces the selected keyframes without changing their order",
    "category": "Animation",
}

import bpy
from bpy.props import BoolProperty, EnumProperty, IntProperty


def _selected_keys(context):
    """All selected keyframes on editable F-curves visible in this editor."""
    fcurves = getattr(context, "editable_fcurves", None) or []
    keys = []
    for fc in fcurves:
        if fc.lock:
            continue
        for kp in fc.keyframe_points:
            if kp.select_control_point:
                keys.append((fc, kp))
    return keys


class ANIM_OT_arrange_keyframes(bpy.types.Operator):
    """Evenly space the selected keyframes, keeping their order"""

    bl_idname = "anim.arrange_keyframes"
    bl_label = "Arrange"
    bl_options = {"REGISTER", "UNDO"}

    mode: EnumProperty(
        name="Spacing",
        items=[
            ("AVERAGE", "Average Gap",
             "Start at the first selected keyframe and use the average gap, rounded to whole frames"),
            ("FIT", "Fit Range",
             "Keep the first and last selected keyframes where they are and spread the rest evenly between"),
            ("CUSTOM", "Custom Gap",
             "Start at the first selected keyframe and use a fixed number of frames between keyframes"),
        ],
        default="AVERAGE",
    )
    gap: IntProperty(
        name="Gap",
        description="Frames between each keyframe (Custom Gap mode)",
        default=5,
        min=1,
    )
    whole_frames: BoolProperty(
        name="Whole Frames",
        description="Snap results to whole frames (Fit Range mode)",
        default=True,
    )

    @classmethod
    def poll(cls, context):
        return getattr(context, "editable_fcurves", None) is not None

    def execute(self, context):
        keys = _selected_keys(context)
        if not keys:
            self.report({"WARNING"}, "No keyframes selected")
            return {"CANCELLED"}

        # Keys on the same frame (different channels) count as one "column"
        # and move together.
        frames = sorted({round(kp.co.x, 4) for _, kp in keys})
        n = len(frames)
        if n < 2:
            self.report({"WARNING"}, "Select keyframes on at least two different frames")
            return {"CANCELLED"}

        first, last = frames[0], frames[-1]

        if self.mode == "AVERAGE":
            gap = max(1, round((last - first) / (n - 1)))
            new_frames = [first + i * gap for i in range(n)]
        elif self.mode == "CUSTOM":
            new_frames = [first + i * self.gap for i in range(n)]
        else:  # FIT
            step = (last - first) / (n - 1)
            new_frames = [first + i * step for i in range(n)]
            if self.whole_frames:
                new_frames = [float(round(f)) for f in new_frames]

        mapping = dict(zip(frames, new_frames))

        touched = set()
        for fc, kp in keys:
            old = round(kp.co.x, 4)
            delta = mapping[old] - kp.co.x
            kp.co.x += delta
            kp.handle_left.x += delta
            kp.handle_right.x += delta
            touched.add(fc)

        for fc in touched:
            fc.update()  # re-sorts keyframes and recalculates auto handles

        for area in context.screen.areas:
            if area.type in {"DOPESHEET_EDITOR", "GRAPH_EDITOR", "TIMELINE"}:
                area.tag_redraw()

        self.report({"INFO"}, f"Arranged {n} keyframe columns")
        return {"FINISHED"}


def _draw_header(self, context):
    self.layout.operator(ANIM_OT_arrange_keyframes.bl_idname, text="Arrange")


def _draw_menu(self, context):
    self.layout.separator()
    self.layout.operator(ANIM_OT_arrange_keyframes.bl_idname, text="Arrange Keyframes")


_header_types = ("DOPESHEET_HT_header", "GRAPH_HT_header")
_menu_types = ("DOPESHEET_MT_key", "GRAPH_MT_key")


def register():
    bpy.utils.register_class(ANIM_OT_arrange_keyframes)
    for name in _header_types:
        t = getattr(bpy.types, name, None)
        if t:
            t.append(_draw_header)
    for name in _menu_types:
        t = getattr(bpy.types, name, None)
        if t:
            t.append(_draw_menu)


def unregister():
    for name in _menu_types:
        t = getattr(bpy.types, name, None)
        if t:
            t.remove(_draw_menu)
    for name in _header_types:
        t = getattr(bpy.types, name, None)
        if t:
            t.remove(_draw_header)
    bpy.utils.unregister_class(ANIM_OT_arrange_keyframes)


if __name__ == "__main__":
    register()
