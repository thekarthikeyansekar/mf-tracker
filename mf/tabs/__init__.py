from importlib import import_module


render_tracker_tab = import_module(
	".3_tracker_tab", package=__name__
).render_tracker_tab
render_holdings_tab = import_module(
	".1_holdings_tab", package=__name__
).render_holdings_tab
render_journey_tab = import_module(
	".2_journey_tab", package=__name__
).render_journey_tab

__all__ = ["render_holdings_tab", "render_journey_tab", "render_tracker_tab"]
