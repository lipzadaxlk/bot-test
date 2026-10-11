"""
ComponentsV2Adapter.py

Provides a ComponentsV2Adapter class with a staticmethod `to_container(content, components, accent_colour=None)`
that converts legacy component structures into disnake.ui.Container with TextDisplay, Separator, ActionRow, etc.

Also defines a no-op `setup(bot)` so automatic extension loaders that import this file as an extension do not fail.
"""



# --- Runtime monkeypatch: force all Buttons to secondary (gray) by default ---
try:
    _orig_button_init = disnake.ui.Button.__init__
    def _patched_button_init(self, *args, **kwargs):
        # If url present, button must be link style
        if 'url' in kwargs and kwargs.get('url') is not None:
            kwargs['style'] = disnake.ButtonStyle.link
        else:
            # Force non-link buttons to secondary
            kwargs['style'] = disnake.ButtonStyle.secondary
        return _orig_button_init(self, *args, **kwargs)
    disnake.ui.Button.__init__ = _patched_button_init
except Exception:
    pass
# --- end monkeypatch ---

import disnake
from typing import Any

class ComponentsV2Adapter:
    @staticmethod
    def _is_button(obj: Any) -> bool:
        try:
            return isinstance(obj, disnake.ui.Button) or hasattr(obj, "style")
        except Exception:
            return False

    @staticmethod
    def _is_select(obj: Any) -> bool:
        try:
            name = obj.__class__.__name__.lower()
            return "select" in name or isinstance(obj, (disnake.ui.Select, disnake.ui.StringSelect))
        except Exception:
            return False

    @staticmethod
    def _normalize_button_style(btn: Any):
        try:
            btn.style = disnake.ButtonStyle.secondary
        except Exception:
            try:
                setattr(btn, "style", disnake.ButtonStyle.secondary)
            except Exception:
                pass
        return btn

    @staticmethod
    def to_container(content: Any = None, components: Any = None, accent_colour=None) -> disnake.ui.Container:
        elems = []

        # Add content as TextDisplay if provided (and not empty)
        if content is not None and content != "":
            elems.append(disnake.ui.TextDisplay(content=str(content)))
            # Add separator between text and buttons as requested
            elems.append(disnake.ui.Separator())

        rows = []

        # If components already a Container, return it (but try normalizing button styles)
        if isinstance(components, disnake.ui.Container):
            try:
                children = getattr(components, "children", None) or getattr(components, "_children", [])
                for child in children:
                    inner = getattr(child, "components", None) or getattr(child, "children", None) or []
                    for c in inner:
                        if ComponentsV2Adapter._is_button(c):
                            ComponentsV2Adapter._normalize_button_style(c)
            except Exception:
                pass
            # If content provided, prepend text elements
            if content is None:
                return components
            else:
                final = disnake.ui.Container(*(elems + list(children)))
                if accent_colour is not None:
                    try:
                        final.accent_colour = disnake.Colour(accent_colour) if not isinstance(accent_colour, disnake.Colour) else accent_colour
                    except Exception:
                        pass
                return final

        # Normalize input types: accept nested lists (rows), single components, ActionRow, etc.
        if components is None:
            cont = disnake.ui.Container(*elems)
            if accent_colour is not None:
                try:
                    cont.accent_colour = disnake.Colour(accent_colour) if not isinstance(accent_colour, disnake.Colour) else accent_colour
                except Exception:
                    pass
            return cont

        # If single non-iterable, wrap it
        if not isinstance(components, (list, tuple)):
            components = [components]

        for item in components:
            # If it's a list/tuple => treat as a row of components
            if isinstance(item, (list, tuple)):
                items = []
                for c in item:
                    if ComponentsV2Adapter._is_button(c):
                        ComponentsV2Adapter._normalize_button_style(c)
                    items.append(c)
                rows.append(disnake.ui.ActionRow(*items))
            else:
                # single item
                if ComponentsV2Adapter._is_button(item):
                    ComponentsV2Adapter._normalize_button_style(item)
                    rows.append(disnake.ui.ActionRow(item))
                elif ComponentsV2Adapter._is_select(item):
                    rows.append(disnake.ui.ActionRow(item))
                elif isinstance(item, disnake.ui.ActionRow):
                    # normalize buttons inside
                    try:
                        inner = getattr(item, "components", None) or getattr(item, "children", None) or []
                        for c in inner:
                            if ComponentsV2Adapter._is_button(c):
                                ComponentsV2Adapter._normalize_button_style(c)
                    except Exception:
                        pass
                    rows.append(item)
                else:
                    # unknown, try to append directly
                    rows.append(item)

        # Insert separator before first row that contains a select (if any) as requested
        select_idx = None
        for idx, row in enumerate(rows):
            try:
                inner = getattr(row, "components", None) or getattr(row, "children", None) or []
                for c in inner:
                    if ComponentsV2Adapter._is_select(c):
                        select_idx = idx
                        break
                if select_idx is not None:
                    break
            except Exception:
                continue

        final_list = list(elems)
        for i, row in enumerate(rows):
            if select_idx is not None and i == select_idx:
                final_list.append(disnake.ui.Separator())
            final_list.append(row)

        cont = disnake.ui.Container(*final_list)
        if accent_colour is not None:
            try:
                cont.accent_colour = disnake.Colour(accent_colour) if not isinstance(accent_colour, disnake.Colour) else accent_colour
            except Exception:
                pass
        return cont

# no-op setup so autoloaders that treat this module as an extension won't fail
def setup(bot):
    return None
    