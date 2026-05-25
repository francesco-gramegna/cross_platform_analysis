"""
Step 8: RQ1 (Predictive extension)

Question: Given an account's platform, content category, audience country,
and follower count, can we predict its engagement rate? How does the
prediction accuracy compare to a traditional OLS baseline?

Target:   log10(er_pct)  — matches RQ1's outcome variable for direct comparison
Features: log10(followers), platform, category_unified, country
Scope:    2022 only, Instagram + YouTube (TikTok 2022 lacks category & country)
Split:    80/20 by unique account (random_state=42)
Models:   OLS (baseline) · Random Forest · XGBoost
Metrics:  R² · RMSE · MAE  (all on log scale)
"""

from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from sklearn.linear_model import LinearRegression
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import r2_score, mean_absolute_error, mean_squared_error
from sklearn.preprocessing import OneHotEncoder
from sklearn.inspection import permutation_importance
import xgboost as xgb

ROOT = Path(__file__).resolve().parents[2]
SRC  = ROOT / "4 - ER unified" / "finalData_with_er.csv"
OUT  = ROOT / "8 - ML prediction"
PLOT = OUT / "plots"
TBL  = OUT / "tables"
PLOT.mkdir(exist_ok=True, parents=True)
TBL.mkdir(exist_ok=True, parents=True)

PLATFORM_COLOR = {"instagram": "#E4405F", "youtube": "#FF0000"}
MODEL_COLOR    = {"OLS (baseline)": "#37474F", "Random Forest": "#2E7D32", "XGBoost": "#C62828"}
EXCLUDE_CATEGORIES = {"Other", "UNMAPPED"}
TOP_K_COUNTRIES = 15
RANDOM_STATE = 42

summary = []
def log(msg=""):
    print(msg); summary.append(str(msg))

# ---------- PNG table helper ------------------------------------------------
def save_table_png(df, path, title=None, fmt=None):
    d = df.copy()
    if fmt is not None:
        for col, f in fmt.items():
            if col in d.columns:
                d[col] = d[col].map(lambda v: f(v) if pd.notna(v) else "")
    else:
        for col in d.select_dtypes("number").columns:
            d[col] = d[col].map(lambda v: f"{v:.3f}" if pd.notna(v) else "")
    if not isinstance(d.index, pd.RangeIndex):
        d = d.reset_index()
    n_rows, n_cols = d.shape
    fig_w = max(8, 1.3 * n_cols); fig_h = 0.6 + 0.38 * (n_rows + 1) + (0.4 if title else 0)
    fig, ax = plt.subplots(figsize=(fig_w, fig_h)); ax.axis("off")
    if title:
        ax.set_title(title, loc="left", fontsize=11, fontweight="bold", pad=10)
    tbl = ax.table(cellText=d.astype(str).values, colLabels=d.columns.astype(str).tolist(),
                   loc="center", cellLoc="center", colLoc="center")
    tbl.auto_set_font_size(False); tbl.set_fontsize(9); tbl.scale(1, 1.25)
    for j in range(n_cols):
        c = tbl[0, j]; c.set_facecolor("#37474F"); c.set_text_props(color="white", fontweight="bold")
    for i in range(1, n_rows + 1):
        for j in range(n_cols):
            if i % 2 == 0:
                tbl[i, j].set_facecolor("#F4F6F7")
    fig.tight_layout(); fig.savefig(path, dpi=160, bbox_inches="tight"); plt.close(fig)

# ===========================================================================
# 1. Load and prepare
# ===========================================================================
df_all = pd.read_csv(SRC, low_memory=False)
df22 = df_all[(df_all["_year"] == 2022)
              & df_all["_platform"].isin(["instagram", "youtube"])
              & df_all["er_pct"].notna() & (df_all["er_pct"] > 0)
              & df_all["followers"].notna() & (df_all["followers"] > 0)
              & df_all["category_unified"].notna()
              & ~df_all["category_unified"].isin(EXCLUDE_CATEGORIES)
              & df_all["country"].notna()].copy()
log(f"Loaded {len(df_all):,} rows; {len(df22):,} valid 2022 IG+YT rows.")

# Restrict to top-K countries per platform (consistent with RQ1)
top_c = {plat: df22[df22["_platform"] == plat]["country"]
                    .value_counts().head(TOP_K_COUNTRIES).index.tolist()
         for plat in ["instagram", "youtube"]}
df22 = df22[df22.apply(lambda r: r["country"] in top_c[r["_platform"]], axis=1)].copy()
log(f"After top-{TOP_K_COUNTRIES}-country filter: {len(df22):,} rows.")

# Dedup to one row per (handle, _platform)
agg = (df22.groupby(["handle", "_platform"])
            .agg(er_pct=("er_pct", "median"),
                 followers=("followers", "median"),
                 category_unified=("category_unified", "first"),
                 country=("country", "first"))
            .reset_index())
agg["log_er"]        = np.log10(agg["er_pct"])
agg["log_followers"] = np.log10(agg["followers"])
log(f"Unique accounts: {len(agg):,}")
log(f"  Instagram: {(agg['_platform']=='instagram').sum():,}")
log(f"  YouTube:   {(agg['_platform']=='youtube').sum():,}")

# ===========================================================================
# 2. Train/test split (80/20 by unique account)
# ===========================================================================
train_df, test_df = train_test_split(agg, test_size=0.20, random_state=RANDOM_STATE,
                                      stratify=agg["_platform"])
log(f"\nTrain: {len(train_df):,} accounts | Test: {len(test_df):,} accounts")

# One-hot encode categoricals; keep continuous as-is
CAT_COLS  = ["_platform", "category_unified", "country"]
CONT_COLS = ["log_followers"]
encoder = OneHotEncoder(sparse_output=False, handle_unknown="ignore")
X_train_cat = encoder.fit_transform(train_df[CAT_COLS])
X_test_cat  = encoder.transform(test_df[CAT_COLS])
X_train = np.hstack([train_df[CONT_COLS].values, X_train_cat])
X_test  = np.hstack([test_df[CONT_COLS].values,  X_test_cat])
y_train = train_df["log_er"].values
y_test  = test_df["log_er"].values
feature_names = CONT_COLS + list(encoder.get_feature_names_out(CAT_COLS))
log(f"Feature count: {X_train.shape[1]} ({len(CONT_COLS)} continuous + "
    f"{X_train_cat.shape[1]} one-hot encoded)")

# ===========================================================================
# 3. Fit three models and evaluate
# ===========================================================================
models = {
    "OLS (baseline)":  LinearRegression(),
    "Random Forest":   RandomForestRegressor(n_estimators=300, max_depth=None,
                                              random_state=RANDOM_STATE, n_jobs=-1),
    "XGBoost":         xgb.XGBRegressor(n_estimators=400, learning_rate=0.05,
                                         max_depth=6, random_state=RANDOM_STATE,
                                         n_jobs=-1, verbosity=0),
}

results, predictions, fitted_models = [], {}, {}
log("\n" + "=" * 70 + "\nMODEL PERFORMANCE (held-out test set)\n" + "=" * 70)
for name, mdl in models.items():
    mdl.fit(X_train, y_train)
    yhat = mdl.predict(X_test)
    r2   = r2_score(y_test, yhat)
    rmse = np.sqrt(mean_squared_error(y_test, yhat))
    mae  = mean_absolute_error(y_test, yhat)
    predictions[name] = yhat
    fitted_models[name] = mdl
    results.append({"model": name, "R2": r2, "RMSE": rmse, "MAE": mae})
    log(f"  {name:<20} R²={r2:.3f}  RMSE={rmse:.3f}  MAE={mae:.3f}")

save_table_png(
    pd.DataFrame(results), TBL / "T1_model_comparison.png",
    title=f"Table 1. Model performance on held-out test set "
          f"(n_train={len(y_train):,}, n_test={len(y_test):,})",
    fmt={"model": str, "R2": lambda v: f"{v:.3f}",
         "RMSE": lambda v: f"{v:.3f}", "MAE": lambda v: f"{v:.3f}"})

# ===========================================================================
# 4. Permutation feature importance (same metric across all 3 models)
# ===========================================================================
log("\n" + "=" * 70 + "\nPERMUTATION FEATURE IMPORTANCE (R² drop)\n" + "=" * 70)
# Group one-hot features back to original block (platform / category / country / followers)
def feature_block(name):
    if name == "log_followers": return "log_followers"
    if name.startswith("_platform"): return "platform"
    if name.startswith("category_unified"): return "category"
    if name.startswith("country"): return "country"
    return name

block_indices = {}
for j, fn in enumerate(feature_names):
    block_indices.setdefault(feature_block(fn), []).append(j)

importance_rows = []
for model_name, mdl in fitted_models.items():
    log(f"\n  {model_name}:")
    for block_name, idxs in block_indices.items():
        # Permute all columns in this block jointly
        rng = np.random.default_rng(RANDOM_STATE)
        importances = []
        for _ in range(15):  # 15 repetitions
            X_perm = X_test.copy()
            perm = rng.permutation(X_test.shape[0])
            X_perm[:, idxs] = X_test[perm][:, idxs]
            r2_perm = r2_score(y_test, mdl.predict(X_perm))
            importances.append(r2_score(y_test, mdl.predict(X_test)) - r2_perm)
        importance_rows.append({"model": model_name, "feature_block": block_name,
                                "importance_mean": np.mean(importances),
                                "importance_std":  np.std(importances)})
        log(f"    {block_name:<15} ΔR² = {np.mean(importances):.4f} (±{np.std(importances):.4f})")

imp_df = pd.DataFrame(importance_rows)
save_table_png(
    imp_df, TBL / "T2_permutation_importance.png",
    title="Table 2. Permutation importance — R² decrease when each feature block is shuffled",
    fmt={"model": str, "feature_block": str,
         "importance_mean": lambda v: f"{v:.4f}",
         "importance_std":  lambda v: f"{v:.4f}"})

# ===========================================================================
# F1: Predicted vs actual scatter, per model
# ===========================================================================
fig, axes = plt.subplots(1, 3, figsize=(15, 5), sharex=True, sharey=True)
lims = (min(y_test.min(), min(p.min() for p in predictions.values())) - 0.2,
        max(y_test.max(), max(p.max() for p in predictions.values())) + 0.2)
for ax, (name, yhat) in zip(axes, predictions.items()):
    # Color points by platform
    test_plats = test_df["_platform"].values
    for plat, color in PLATFORM_COLOR.items():
        m = test_plats == plat
        ax.scatter(y_test[m], yhat[m], s=10, alpha=0.45, color=color,
                   label=plat.capitalize() if ax is axes[0] else None)
    ax.plot(lims, lims, color="black", lw=0.8, ls="--")
    r2 = r2_score(y_test, yhat)
    ax.text(0.05, 0.92, f"R² = {r2:.3f}", transform=ax.transAxes,
            fontsize=11, bbox=dict(facecolor="white", edgecolor="gray"))
    ax.set_xlabel("Actual log10(er_pct)")
    ax.set_ylabel("Predicted log10(er_pct)")
    ax.set_title(name)
    ax.set_xlim(lims); ax.set_ylim(lims)
axes[0].legend(loc="lower right", fontsize=9)
fig.suptitle("Predicted vs actual engagement rate, by model", y=1.00)
fig.tight_layout(); fig.savefig(PLOT / "F1_predicted_vs_actual.png", dpi=160); plt.close(fig)
log(f"\nSaved {PLOT/'F1_predicted_vs_actual.png'}")

# ===========================================================================
# F2: Feature importance bar chart, per model
# ===========================================================================
blocks = sorted(block_indices.keys())
fig, ax = plt.subplots(figsize=(9, 4.5))
width = 0.25
x_pos = np.arange(len(blocks))
for i, (name, color) in enumerate(MODEL_COLOR.items()):
    sub = imp_df[imp_df["model"] == name].set_index("feature_block").reindex(blocks)
    ax.bar(x_pos + i * width, sub["importance_mean"], width,
           yerr=sub["importance_std"], capsize=3,
           label=name, color=color, alpha=0.85, edgecolor="white")
ax.set_xticks(x_pos + width); ax.set_xticklabels(blocks)
ax.set_ylabel("Permutation Δ R²  (higher = more important)")
ax.set_title("Feature importance by block (permutation importance on test set)")
ax.legend()
ax.axhline(0, color="gray", lw=0.5, ls=":")
fig.tight_layout(); fig.savefig(PLOT / "F2_feature_importance.png", dpi=160); plt.close(fig)
log(f"Saved {PLOT/'F2_feature_importance.png'}")

# ===========================================================================
# F3: Residual distribution per model
# ===========================================================================
fig, axes = plt.subplots(1, 3, figsize=(15, 4), sharex=True, sharey=True)
for ax, (name, yhat) in zip(axes, predictions.items()):
    resid = y_test - yhat
    ax.hist(resid, bins=40, color=MODEL_COLOR[name], alpha=0.8)
    ax.axvline(0, color="black", lw=0.8, ls="--")
    ax.set_xlabel("Residual (actual − predicted)  in log10 units")
    ax.set_title(f"{name}\nmean={resid.mean():+.3f}, std={resid.std():.3f}")
fig.suptitle("Residual distribution on held-out test set", y=1.02)
fig.tight_layout(); fig.savefig(PLOT / "F3_residuals.png", dpi=160); plt.close(fig)
log(f"Saved {PLOT/'F3_residuals.png'}")

# ===========================================================================
# Save summary
# ===========================================================================
(OUT / "summary.txt").write_text("\n".join(summary))
print(f"\nSaved summary to {OUT/'summary.txt'}")
print(f"Saved {len(list(TBL.glob('*.png')))} tables to {TBL}")
print(f"Saved {len(list(PLOT.glob('*.png')))} plots to {PLOT}")
