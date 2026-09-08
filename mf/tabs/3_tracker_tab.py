import plotly.graph_objects as go
import streamlit as st

from utils.helpers import fmt_int, fmt_inr
from mf.utils.nav_advsior import calculate_nav_advisor


def render_tracker_tab(df):
	tracker_vendors = [
		vendor for vendor in ("Axis", "DSP")
		if not df[df["vendor"] == vendor].empty
	]
	if not tracker_vendors:
		st.info("No fund data available.")
		return

	col_1, col_2, col_3 = st.columns([1,3,2])
	with col_1:

		selected_vendor = st.selectbox("Vendor", tracker_vendors)
		if not selected_vendor:
			return

		vendor_df = df[df["vendor"] == selected_vendor]
		tracker_funds = list(vendor_df["n_id"].unique())
		selected_fund = st.selectbox("Fund Name", tracker_funds)
		if not selected_fund:
			return

		group = vendor_df[vendor_df["n_id"] == selected_fund]
		dated = group[group["date_parsed"].notna()].sort_values("date_parsed")

	with col_2:
		st.markdown("#### Investment Timeline")

		fig = go.Figure()
		fig.add_trace(
			go.Scatter(
				x=dated["date_parsed"].dt.date,
				y=dated["bought_nav"],
				mode="markers",
				name="Invested NAV",
			)
		)

		current_nav_values = group["nav"].dropna()
		if not current_nav_values.empty:
			current_nav = current_nav_values.iloc[-1]
			# st.text("Current Nav : " + str(current_nav))
			fig.add_hline(
				y=current_nav,
				line_color="red",
				line_dash="dot",
				annotation_text="Current NAV : " + str(current_nav),
			)

		fig.update_layout(
			xaxis_title="Date",
			xaxis_tickangle=300,
			yaxis_title="NAV",
			hovermode="closest",
		)
		st.plotly_chart(fig, use_container_width=True)

		with col_3:
			## NAV Advisor

			if not current_nav_values.empty:
				advisor = calculate_nav_advisor(group, return_above_df=True)

				st.markdown("#### NAV Advisor")
				advisor_cols = st.columns(4)
				advisor_cols[0].metric("Transactions Above", fmt_int(advisor["transactions_above"]))
				advisor_cols[1].metric("Transactions Below", fmt_int(advisor["transactions_below"]))
				advisor_cols[2].metric("Units Above", fmt_int(advisor["units_above"]))
				advisor_cols[3].metric("Units Below", fmt_int(advisor["units_below"]))


				# st.markdown("#### Averaging Advisor")
				average_advisor_cols = st.columns(4)
				average_advisor_cols[0].metric("To Average Units", fmt_int(advisor["to_average_units"]))
				average_advisor_cols[1].metric("To Average Amount", fmt_inr(advisor["to_average_amount"]))
				average_advisor_cols[2].metric("Averaging Invested", fmt_inr(advisor["averaging_invested_coverage"]))
				average_advisor_cols[3].metric("Averaging Loss", fmt_inr(advisor["averaging_loss"]))

				if advisor["averaging_loss"] < 0:
					st.markdown("#### Averaging Loss")
					above_df = advisor["above_df"].copy()
					above_df["loss_pct"] = (
						(above_df["bought_nav"] - current_nav)
						/ above_df["bought_nav"]
						* 100
					)
					above_df = above_df.sort_values(by="loss_pct", ascending=False)
					loss_threshold = st.slider(
						"Minimum NAV loss",
						min_value=1,
						max_value=20,
						value=5,
						format="%d%%",
					)
					above_df = above_df[above_df["loss_pct"] >= loss_threshold]
					above_df = above_df.rename(
						columns={"invested": "amount"}
					)
					tmp_units = above_df["units"].sum()
					st.text("Units : " + fmt_int(tmp_units))
					st.text("Amount : " + fmt_inr(tmp_units * current_nav))
					st.dataframe(above_df, hide_index=True, use_container_width=True)
					
					