
import pandas as pd

df = pd.read_csv("Superstore.csv", encoding="cp1252")

print("Dataset Shape:", df.shape)

print("\nMissing Values:")
print(df[["Sales", "Profit", "Discount"]].isna().sum())

print("\nDescriptive Statistics:")
print(df[["Sales", "Profit", "Discount"]].describe())

from scipy.stats import pearsonr

df["Profit Margin"] = df["Profit"] / df["Sales"]

analysis_df = df.loc[
    (df["Sales"] > 0) &
    df["Discount"].notna() &
    df["Profit Margin"].notna()
].copy()

r, p_value = pearsonr(
    analysis_df["Discount"],
    analysis_df["Profit Margin"]
)

print("\n--- Pearson Correlation Analysis ---")
print(f"Number of observations: {len(analysis_df)}")
print(f"Pearson Correlation (r): {r:.4f}")
print(f"P-value: {p_value:.6g}")

if p_value < 0.05:
    print("Result: Statistically significant correlation")
else:
    print("Result: No statistically significant correlation")

    
from scipy.stats import linregress

model = linregress(
    analysis_df["Discount"],
    analysis_df["Profit Margin"]
)

print("\n--- Linear Regression Analysis ---")
print(f"Intercept: {model.intercept:.4f}")
print(f"Slope: {model.slope:.4f}")
print(f"R-squared: {model.rvalue**2:.4f}")
print(f"P-value: {model.pvalue:.6g}")

change = model.slope * 0.10 * 100

print(f"Margin change per +10 pp discount: {change:.2f} percentage points")


import statsmodels.formula.api as smf

multiple_model = smf.ols(
    'Q("Profit Margin") ~ Discount + Quantity + C(Category) + C(Segment)',
    data=analysis_df
).fit(
    cov_type="cluster",
    cov_kwds={"groups": analysis_df["Order ID"]}
)

beta = multiple_model.params["Discount"]
ci = multiple_model.conf_int().loc["Discount"]

print("\n--- Multiple Linear Regression ---")
print(f"R-squared: {multiple_model.rsquared:.4f}")
print(f"Adjusted R-squared: {multiple_model.rsquared_adj:.4f}")
print(f"Discount Coefficient: {beta:.4f}")
print(f"Discount P-value: {multiple_model.pvalues['Discount']:.6g}")
print(f"95% CI for Discount: [{ci.iloc[0]:.4f}, {ci.iloc[1]:.4f}]")

print(
    f"Margin change per +10 pp discount: "
    f"{beta * 10:.2f} percentage points"
)


# -----------------------------------
# Category-Level Statistical Analysis
# -----------------------------------

print("\n--- Category-Level Analysis ---")

category_results = []

for category, group in analysis_df.groupby("Category"):

    category_r, category_p = pearsonr(
        group["Discount"],
        group["Profit Margin"]
    )

    total_sales = group["Sales"].sum()
    total_profit = group["Profit"].sum()

    category_results.append({
        "Category": category,
        "Observations": len(group),
        "Pearson r": round(category_r, 4),
        "P-value": category_p,
        "Profit Margin %": round(
            total_profit / total_sales * 100, 2
        )
    })

category_df = pd.DataFrame(category_results)

print(category_df.to_string(index=False))

category_df.to_csv(
    "category_statistical_results.csv",
    index=False
)

# -----------------------------------
# Discount × Category Interaction
# -----------------------------------

interaction_model = smf.ols(
    'Q("Profit Margin") ~ Discount * C(Category) + Quantity + C(Segment)',
    data=analysis_df
).fit(
    cov_type="cluster",
    cov_kwds={"groups": analysis_df["Order ID"]}
)

print("\n--- Interaction Analysis ---")

print(f"R-squared: {interaction_model.rsquared:.4f}")
print(f"Adjusted R-squared: {interaction_model.rsquared_adj:.4f}")

base_slope = interaction_model.params["Discount"]

for category in ["Furniture", "Office Supplies", "Technology"]:

    if category == "Furniture":
        slope = base_slope
    else:
        term = f"Discount:C(Category)[T.{category}]"
        slope = base_slope + interaction_model.params[term]

    print(f"{category} slope: {slope:.4f}")

test = interaction_model.wald_test(
    "Discount:C(Category)[T.Office Supplies] = 0, "
    "Discount:C(Category)[T.Technology] = 0",
    scalar=True
)

print(f"Interaction P-value: {test.pvalue:.6g}")

import matplotlib.pyplot as plt
from scipy import stats

# -----------------------------------
# Regression Diagnostics
# -----------------------------------

residuals = interaction_model.resid * 100
fitted = interaction_model.fittedvalues * 100

print("\n--- Regression Diagnostics ---")
print("Residual Mean:", round(residuals.mean(), 4))
print("Residual Std:", round(residuals.std(), 4))

fig, axes = plt.subplots(1, 2, figsize=(12, 5))

axes[0].scatter(
    fitted,
    residuals,
    alpha=0.2,
    s=8
)

axes[0].axhline(0, color="red", linestyle="--")
axes[0].set_title("Residuals vs Fitted")
axes[0].set_xlabel("Predicted Profit Margin (%)")
axes[0].set_ylabel("Residual (percentage points)")

stats.probplot(
    residuals,
    dist="norm",
    plot=axes[1]
)

axes[1].set_title("Normal Q-Q Plot")

plt.tight_layout()

plt.savefig(
    "regression_diagnostics.png",
    dpi=300,
    bbox_inches="tight"
)

plt.show()


# -----------------------------------
# Outlier Investigation
# -----------------------------------

diagnostic_df = analysis_df.loc[
    interaction_model.resid.index
].copy()

diagnostic_df["Residual (pp)"] = (
    interaction_model.resid * 100
)

diagnostic_df["Actual Margin %"] = (
    diagnostic_df["Profit Margin"] * 100
)

diagnostic_df["Absolute Residual"] = (
    diagnostic_df["Residual (pp)"].abs()
)

outliers = diagnostic_df.sort_values(
    "Absolute Residual",
    ascending=False
)

print("\n--- Outlier Investigation ---")

print("\nTop 10 Largest Absolute Residuals:")

columns = [
    "Category",
    "Sub-Category",
    "Sales",
    "Profit",
    "Discount",
    "Actual Margin %",
    "Residual (pp)"
]

print(
    outliers[columns].head(10)
    .round(2)
    .to_string(index=False)
)

print("\nObservations with |Residual| > 50 pp:")

print(
    (diagnostic_df["Absolute Residual"] > 50).sum()
)


# -----------------------------------
# High Discount Risk Analysis
# -----------------------------------

print("\n--- High Discount Risk Analysis ---")

appliances = analysis_df[
    analysis_df["Sub-Category"] == "Appliances"
].copy()

high_discount = appliances[
    appliances["Discount"].round(2) == 0.80
]

other_discounts = appliances[
    appliances["Discount"].round(2) != 0.80
]

for name, group in [
    ("Appliances - 80% Discount", high_discount),
    ("Appliances - Other Discounts", other_discounts)
]:
    total_sales = group["Sales"].sum()
    total_profit = group["Profit"].sum()

    profit_margin = (
        total_profit / total_sales * 100
        if total_sales > 0 else float("nan")
    )

    print(f"\n{name}")
    print(f"Observations: {len(group)}")
    print(f"Loss-making records: {(group['Profit'] < 0).sum()}")
    print(f"Total Sales: ${total_sales:,.2f}")
    print(f"Total Profit: ${total_profit:,.2f}")
    print(f"Profit Margin: {profit_margin:.2f}%")


# -----------------------------------
# Sensitivity Analysis
# -----------------------------------

print("\n--- Sensitivity Analysis ---")

reduced_df = analysis_df[
    analysis_df["Discount"].round(2) != 0.80
].copy()

reduced_model = smf.ols(
    'Q("Profit Margin") ~ Discount * C(Category) + Quantity + C(Segment)',
    data=reduced_df
).fit(
    cov_type="cluster",
    cov_kwds={"groups": reduced_df["Order ID"]}
)

print("Original Observations:", len(analysis_df))
print("Reduced Observations:", len(reduced_df))

print("\nOriginal R-squared:",
      round(interaction_model.rsquared, 4))

print("Reduced R-squared:",
      round(reduced_model.rsquared, 4))

print("\nOriginal Furniture Discount Slope:",
      round(interaction_model.params["Discount"], 4))

print("Reduced Furniture Discount Slope:",
      round(reduced_model.params["Discount"], 4))


# -----------------------------------
# Compare Category Slopes
# -----------------------------------

def get_discount_slope(model, category):
    slope = model.params["Discount"]

    if category != "Furniture":
        term = f"Discount:C(Category)[T.{category}]"
        slope += model.params[term]

    return slope


print("\n--- Category Sensitivity Comparison ---")

for category in [
    "Furniture",
    "Office Supplies",
    "Technology"
]:
    original = get_discount_slope(
        interaction_model, category
    )

    reduced = get_discount_slope(
        reduced_model, category
    )

    print(f"\n{category}")
    print(f"Original Slope: {original:.4f}")
    print(f"Reduced Slope: {reduced:.4f}")
    print(f"Difference: {reduced - original:.4f}")

