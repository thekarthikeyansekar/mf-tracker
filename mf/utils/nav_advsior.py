from pathlib import Path

import pandas as pd
import streamlit as st

NAV_ADVISOR_COLUMNS = [
	"transactions_above",
	"transactions_below",
	"units_above",
	"units_below",
	"to_average_units",
	"to_average_amount",
]


def calculate_nav_advisor(group, return_above_df=False):
	"""Calculate NAV advisor metrics for one fund's transaction history."""
	current_nav_values = group["nav"].dropna()
	current_nav = current_nav_values.iloc[-1] if not current_nav_values.empty else None

	metrics = {column: 0.0 for column in NAV_ADVISOR_COLUMNS}
	if current_nav is None or current_nav <= 0:
		return {"bought_nav": current_nav, **metrics}

	dated = group[group["date_parsed"].notna()]
	advisor_df = dated[["bought_nav", "invested"]].copy()
	advisor_df["bought_nav"] = pd.to_numeric(advisor_df["bought_nav"], errors="coerce")
	advisor_df["invested"] = pd.to_numeric(advisor_df["invested"], errors="coerce")
	advisor_df = advisor_df[advisor_df["bought_nav"] > 0].copy()
	advisor_df["units"] = advisor_df["invested"] / advisor_df["bought_nav"]

	above_df = advisor_df[advisor_df["bought_nav"] > current_nav]
	below_df = advisor_df[advisor_df["bought_nav"] < current_nav]
	averaging_units = above_df["units"].sum()
	averaging_amount = averaging_units * current_nav
	to_averaging_invested_amount = above_df["invested"].sum()

    # Averaging Loss
	averaging_loss = averaging_amount - to_averaging_invested_amount

	metrics.update(
		transactions_above=float(len(above_df)),
		transactions_below=float(len(below_df)),
		units_above=float(above_df["units"].sum()),
		units_below=float(below_df["units"].sum()),
		to_average_units=float(averaging_units),
		to_average_amount=float(averaging_amount),
		averaging_loss=float(averaging_loss),
		averaging_invested_coverage = float(to_averaging_invested_amount)
	)
	if return_above_df:
		metrics.update(above_df=above_df)
	
	return {"bought_nav": current_nav, **metrics}


def analyze_nav_advisor(df):
	"""Calculate NAV advisor metrics for every vendor/fund/folio pair."""
	rows = []
	tmp_NAV_ADVISOR_COLUMNS = NAV_ADVISOR_COLUMNS[:]
	
	LOSS_PCT_THRESHOLDS = [3, 5, 10]
	for loss_threshold in LOSS_PCT_THRESHOLDS:
		tmp_NAV_ADVISOR_COLUMNS.append(str(loss_threshold) + "_perc_units")
		tmp_NAV_ADVISOR_COLUMNS.append(str(loss_threshold) + "_perc_amounts")

	for (vendor, fund, f_id), group in df.groupby(
		["vendor", "n_id", "f_id"], sort=False
	):
		metrics = calculate_nav_advisor(group, return_above_df=True)
		tmp_dict = {"vendor": vendor, "fund": fund, "f_id": f_id, **metrics}
		above_df = metrics["above_df"]

		if not above_df.empty:
			current_nav_values = group["nav"].dropna()
			current_nav = current_nav_values.iloc[-1] if not current_nav_values.empty else None
			above_df["loss_pct"] = (
				(above_df["bought_nav"] - current_nav)
				/ above_df["bought_nav"]
				* 100
			)
			above_df = above_df.sort_values(by="loss_pct", ascending=False)
			st.text(fund)
			st.dataframe(above_df)
			
			for loss_threshold in LOSS_PCT_THRESHOLDS:
				above_dff = above_df[above_df["loss_pct"] >= loss_threshold]
				tmp_units = above_dff["units"].sum()
				tmp_amount = tmp_units * current_nav

				tmp_dict.update({
					str(loss_threshold) + "_perc_units" : float(tmp_units),
					str(loss_threshold) + "_perc_amounts" : float(tmp_amount)
				})

		# above_df["delta"] = current_nav - above_df["bought_nav"]
		# above_df = above_df[above_df["delta"] <= -0.40]
	
		rows.append(tmp_dict)

		st.dataframe(pd.DataFrame(rows))

	return pd.DataFrame(
		rows,
		columns=["vendor", "fund", "f_id", "bought_nav", *tmp_NAV_ADVISOR_COLUMNS],
	)


def write_nav_advisor_csv(df, path="nav_advisor.csv"):
	"""Write NAV advisor results to CSV and return the resolved output path."""
	output_path = Path(path)
	df.to_csv(output_path, index=False)
	return output_path
