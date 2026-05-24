library(dplyr)
library(ggplot2)
library(readr)
library(patchwork)

df <- read.csv("dataset/final.csv", stringsAsFactors = FALSE)

# -----------------------------
# Category groups
# -----------------------------

ai_susceptible <- c("Knowledge&Info", "Entertainment")
unsure <- c("Tech&Gaming", "Lifestyle")
human <- c("Sports", "Music", "Beauty&Fashion")

valid_categories <- c(ai_susceptible, unsure, human)

category_group <- function(cat) {
  case_when(
    cat %in% ai_susceptible ~ "AI-susceptible",
    cat %in% unsure ~ "Unsure",
    cat %in% human ~ "Human",
    TRUE ~ NA_character_
  )
}

calc_cv <- function(x) {
  x <- x[!is.na(x)]
  if (length(x) < 2) return(NA_real_)
  if (mean(x) == 0) return(NA_real_)
  sd(x) / mean(x)
}

# -----------------------------
# Clean data
# -----------------------------

df_clean <- df %>%
  mutate(
    er_pct = parse_number(as.character(er_pct)),
    X_year = as.character(X_year),
    X_month = tolower(as.character(X_month)),
    X_platform = tolower(as.character(X_platform)),
    X_is_global = as.character(X_is_global),
    populated_category = as.character(populated_category),
    uniqueId = as.character(uniqueId)
  ) %>%
  filter(
    !is.na(uniqueId),
    uniqueId != "",
    !is.na(X_platform),
    X_platform != "",
    !is.na(populated_category),
    populated_category != "",
    populated_category != "UNMAPPED",
    populated_category %in% valid_categories,
    !is.na(er_pct)
  )

# -----------------------------
# Analysis function
# -----------------------------

run_platform_analysis <- function(platform_name, comparison_year, n_boot = 10000) {

  before <- df_clean %>%
    filter(
      X_platform == platform_name,
      X_year == "2022",
      X_month == "march"
    )

  if (platform_name == "youtube") {
    after <- df_clean %>%
      filter(
        X_platform == platform_name,
        X_year == as.character(comparison_year)
      )
  } else {
    after <- df_clean %>%
      filter(
        X_platform == platform_name,
        X_year == as.character(comparison_year)
      )
  }

  matched <- before %>%
    select(
      uniqueId,
      X_platform,
      category_2022 = populated_category,
      er_2022 = er_pct
    ) %>%
    inner_join(
      after %>%
        select(
          uniqueId,
          X_platform,
          category_after = populated_category,
          er_after = er_pct
        ),
      by = c("uniqueId", "X_platform")
    ) %>%
    filter(
      !is.na(er_2022),
      !is.na(er_after),
      category_2022 %in% valid_categories,
      category_after %in% valid_categories,
      category_2022 == category_after
    ) %>%
    mutate(
      populated_category = category_2022,
      group = category_group(populated_category)
    )

  if (nrow(matched) == 0) {
    warning("No matched rows for platform: ", platform_name)
    return(NULL)
  }

  # -----------------------------
  # Delta CV + p-value per category
  # -----------------------------

  category_results <- lapply(valid_categories, function(cat) {

    cat_df <- matched %>%
      filter(populated_category == cat)

    cv_2022 <- calc_cv(cat_df$er_2022)
    cv_after <- calc_cv(cat_df$er_after)
    delta_cv <- cv_after - cv_2022

    if (nrow(cat_df) >= 2) {

      boot_diffs_cat <- replicate(n_boot, {
        sampled_rows <- sample(seq_len(nrow(cat_df)), replace = TRUE)

        s22 <- cat_df$er_2022[sampled_rows]
        safter <- cat_df$er_after[sampled_rows]

        calc_cv(safter) - calc_cv(s22)
      })

      # One-sided convergence p-value:
      # low p-value = stronger evidence that CV decreased
      p_value_cat <- mean(boot_diffs_cat >= 0, na.rm = TRUE)

    } else {
      p_value_cat <- NA_real_
    }

    data.frame(
      populated_category = cat,
      group = category_group(cat),
      n_matched = nrow(cat_df),
      cv_2022 = cv_2022,
      cv_after = cv_after,
      delta_cv = delta_cv,
      p_value = p_value_cat
    )

  }) %>%
    bind_rows() %>%
    filter(!is.na(delta_cv))

  # -----------------------------
  # Bootstrap p-value for AI group
  # -----------------------------

  ai_df <- matched %>%
    filter(populated_category %in% ai_susceptible)

  if (nrow(ai_df) >= 2) {

    observed_ai_delta <- calc_cv(ai_df$er_after) - calc_cv(ai_df$er_2022)

    boot_diffs <- replicate(n_boot, {
      sampled_rows <- sample(seq_len(nrow(ai_df)), replace = TRUE)

      s22 <- ai_df$er_2022[sampled_rows]
      safter <- ai_df$er_after[sampled_rows]

      calc_cv(safter) - calc_cv(s22)
    })

    p_value_ai_convergence <- mean(boot_diffs >= 0, na.rm = TRUE)

  } else {
    observed_ai_delta <- NA_real_
    p_value_ai_convergence <- NA_real_
  }

  category_results <- category_results %>%
    mutate(
      populated_category = factor(
        populated_category,
        levels = category_results$populated_category[order(category_results$delta_cv)]
      ),
      bar_label = paste0(
        sprintf("%.2f", delta_cv),
        "\n",
        "p=",
        ifelse(is.na(p_value), "NA", sprintf("%.2f", p_value))
      )
    )

  subtitle_text <- paste0(
    "Matched same uniqueId, same platform, same category \n 2022 March vs ",
    comparison_year,
    ifelse(platform_name == "youtube", "", " global")
  )

  caption_text <- paste0(
    "AI p-value = ",
    ifelse(is.na(p_value_ai_convergence), "NA", signif(p_value_ai_convergence, 4)),
    " \n AI matched rows = ",
    nrow(ai_df),
    " \n Total matched rows = ",
    nrow(matched)
  )

  p <- ggplot(
    category_results,
    aes(x = populated_category, y = delta_cv, fill = group)
  ) +
    geom_hline(yintercept = 0, color = "black", linewidth = 0.4) +
    geom_col(width = 0.75) +
    geom_text(
      aes(
        label = bar_label,
        vjust = ifelse(delta_cv >= 0, -0.25, 1.15)
      ),
      size = 3,
      lineheight = 0.9
    ) +
    scale_fill_manual(
      values = c(
        "AI-susceptible" = "red",
        "Unsure" = "grey60",
        "Human" = "steelblue"
      )
    ) +
    labs(
      title = paste0(platform_name, ": Delta CV by Category"),
      subtitle = subtitle_text,
      x = NULL,
      y = "Delta CV",
      fill = "Group",
      caption = caption_text
    ) +
    theme_minimal(base_size = 12) +
    theme(
      axis.text.x = element_text(angle = 35, hjust = 1),
      plot.caption = element_text(size = 9, hjust = 0.5),
      legend.position = "bottom"
    )

  return(list(
    platform = platform_name,
    comparison_year = comparison_year,
    plot = p,
    category_results = category_results,
    observed_ai_delta = observed_ai_delta,
    p_value_ai_convergence = p_value_ai_convergence,
    n_ai_matched = nrow(ai_df),
    n_total_matched = nrow(matched)
  ))
}

# -----------------------------
# Run each platform
# -----------------------------

instagram_results <- run_platform_analysis("instagram", 2024)
tiktok_results    <- run_platform_analysis("tiktok", 2024)
youtube_results   <- run_platform_analysis("youtube", 2026)

all_results <- list(
  instagram = instagram_results,
  tiktok = tiktok_results,
  youtube = youtube_results
)

# -----------------------------
# Use common centered y-axis
# -----------------------------

all_delta_values <- unlist(
  lapply(all_results, function(x) {
    if (is.null(x)) return(NULL)
    x$category_results$delta_cv
  })
)

max_abs_y <- max(abs(all_delta_values), na.rm = TRUE)

if (!is.finite(max_abs_y) || max_abs_y == 0) {
  max_abs_y <- 0.01
}

all_results <- lapply(all_results, function(x) {
  if (is.null(x)) return(NULL)

  x$plot <- x$plot +
    scale_y_continuous(
      limits = c(-max_abs_y, max_abs_y),
      expand = expansion(mult = c(0.18, 0.18))
    )

  x
})

# -----------------------------
# Plot all three side by side
# -----------------------------

combined_plot <- (
  all_results$instagram$plot |
    all_results$tiktok$plot |
    all_results$youtube$plot
) +
  plot_layout(guides = "collect", nrow = 1) &
  theme(
    legend.position = "bottom",
    axis.text.x = element_text(angle = 45, hjust = 1, size = 8),
    plot.title = element_text(size = 11),
    plot.subtitle = element_text(size = 10),
    plot.caption = element_text(size = 10, hjust = 0.5)
  )

print(combined_plot)

# -----------------------------
# Print category-level p-value summary
# -----------------------------

pvalue_summary <- do.call(
  rbind,
  lapply(all_results, function(x) {
    if (is.null(x)) return(NULL)

    x$category_results %>%
      mutate(
        platform = x$platform,
        comparison = paste0("2022 March vs ", x$comparison_year)
      ) %>%
      select(
        platform,
        comparison,
        populated_category,
        group,
        n_matched,
        cv_2022,
        cv_after,
        delta_cv,
        p_value
      )
  })
)

print(pvalue_summary)

# -----------------------------
# Optional save
# -----------------------------

ggsave(
  filename = "delta_cv_all_platforms_side_by_side.png",
  plot = combined_plot,
  width = 12,
  height = 6,
  dpi = 300
)
