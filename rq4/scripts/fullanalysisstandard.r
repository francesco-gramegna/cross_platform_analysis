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
# Important:
# Do NOT filter categories here.
# We first select the top N, then filter category.
# -----------------------------

df_clean <- df %>%
  mutate(
    er_pct = parse_number(as.character(er_pct)),
    followers = parse_number(as.character(followers)),
    X_year = as.character(X_year),
    X_month = tolower(as.character(X_month)),
    X_platform = tolower(as.character(X_platform)),
    X_is_global = as.character(X_is_global),
    populated_category = as.character(populated_category)
  ) %>%
  filter(
    !is.na(X_platform),
    X_platform != "",
    X_platform %in% c("instagram", "tiktok"),
    !is.na(er_pct),
    !is.na(followers)
  )

# -----------------------------
# Analysis function:
# Instagram 2022: top 300
# Everything else: top 100
# Then filter to valid populated categories
# Then compute delta CV and per-category p-value
# -----------------------------

run_platform_analysis_top100 <- function(platform_name, n_boot = 10000) {

  before_n <- ifelse(platform_name == "instagram", 300, 100)

  # 2022 baseline:
  # March only, NO global filter.
  # First take top N, THEN filter category.
  before <- df_clean %>%
    filter(
      X_platform == platform_name,
      X_year == "2022",
      X_month == "march"
    ) %>%
    arrange(desc(followers)) %>%
    slice_head(n = before_n) %>%
    filter(
      !is.na(populated_category),
      populated_category != "",
      populated_category != "UNMAPPED",
      populated_category %in% valid_categories
    )

  # 2024 comparison:
  # Global only.
  # First take top 100, THEN filter category.
  after <- df_clean %>%
    filter(
      X_platform == platform_name,
      X_year == "2024",
      X_is_global == "True"
    ) %>%
    arrange(desc(followers)) %>%
    slice_head(n = 100) %>%
    filter(
      !is.na(populated_category),
      populated_category != "",
      populated_category != "UNMAPPED",
      populated_category %in% valid_categories
    )

  if (nrow(before) == 0 || nrow(after) == 0) {
    warning("Missing before or after rows for platform: ", platform_name)
    return(NULL)
  }

  # -----------------------------
  # Delta CV + bootstrap p-value per category
  # -----------------------------

  category_results <- lapply(valid_categories, function(cat) {

    vals_2022 <- before %>%
      filter(populated_category == cat) %>%
      pull(er_pct)

    vals_2024 <- after %>%
      filter(populated_category == cat) %>%
      pull(er_pct)

    cv_2022 <- calc_cv(vals_2022)
    cv_2024 <- calc_cv(vals_2024)
    delta_cv <- cv_2024 - cv_2022

    if (length(vals_2022) >= 2 && length(vals_2024) >= 2) {

      boot_diffs <- replicate(n_boot, {
        s22 <- sample(vals_2022, replace = TRUE)
        s24 <- sample(vals_2024, replace = TRUE)

        calc_cv(s24) - calc_cv(s22)
      })

      # One-sided convergence test:
      # low p-value = stronger evidence that CV decreased
      p_value <- mean(boot_diffs >= 0, na.rm = TRUE)

    } else {
      p_value <- NA_real_
    }

    data.frame(
      populated_category = cat,
      group = category_group(cat),
      n_2022 = length(vals_2022),
      n_2024 = length(vals_2024),
      cv_2022 = cv_2022,
      cv_2024 = cv_2024,
      delta_cv = delta_cv,
      p_value = p_value
    )

  }) %>%
    bind_rows() %>%
    filter(!is.na(delta_cv))

  if (nrow(category_results) == 0) {
    warning("No valid category-level CV results for platform: ", platform_name)
    return(NULL)
  }

  category_results <- category_results %>%
    mutate(
      populated_category = factor(
        populated_category,
        levels = populated_category[order(delta_cv)]
      ),
      bar_label = paste0(
        sprintf("%.2f", delta_cv),
        "\n",
        "p=",
        ifelse(is.na(p_value), "NA", sprintf("%.2f", p_value))
      )
    )

  subtitle_text <- paste0(
    ifelse(
      platform_name == "instagram",
      "2022 March top 300 vs 2024 global top 100",
      "2022 March top 100 vs 2024 global top 100"
    ),
    " | category filter applied after top-N selection"
  )

  caption_text <- paste0(
    "Categorized rows after top-N: 2022 = ",
    nrow(before),
    " | 2024 = ",
    nrow(after)
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
      y = "Delta CV: CV 2024 - CV 2022",
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
    plot = p,
    category_results = category_results,
    n_total_2022 = nrow(before),
    n_total_2024 = nrow(after),
    before_n = before_n,
    after_n = 100
  ))
}

# -----------------------------
# Run Instagram and TikTok only
# -----------------------------

instagram_results <- run_platform_analysis_top100("instagram")
tiktok_results <- run_platform_analysis_top100("tiktok")

all_results <- list(
  instagram = instagram_results,
  tiktok = tiktok_results
)

all_results <- all_results[!sapply(all_results, is.null)]

# -----------------------------
# Use common centered y-axis
# -----------------------------

all_delta_values <- unlist(
  lapply(all_results, function(x) {
    x$category_results$delta_cv
  })
)

max_abs_y <- max(abs(all_delta_values), na.rm = TRUE)

if (!is.finite(max_abs_y) || max_abs_y == 0) {
  max_abs_y <- 0.01
}

all_results <- lapply(all_results, function(x) {
  x$plot <- x$plot +
    scale_y_continuous(
      limits = c(-max_abs_y, max_abs_y),
      expand = expansion(mult = c(0.20, 0.20))
    )

  x
})

# -----------------------------
# Plot side by side
# -----------------------------

combined_plot <- (
  all_results$instagram$plot |
  all_results$tiktok$plot
) +
  plot_layout(guides = "collect", nrow = 1) &
  theme(
    legend.position = "bottom",
    axis.text.x = element_text(angle = 45, hjust = 1, size = 8),
    plot.title = element_text(size = 11),
    plot.subtitle = element_text(size = 9),
    plot.caption = element_text(size = 9, hjust = 0.5)
  )

print(combined_plot)

# -----------------------------
# Print category-level p-value summary
# -----------------------------

pvalue_summary <- do.call(
  rbind,
  lapply(all_results, function(x) {
    x$category_results %>%
      mutate(
        platform = x$platform,
        comparison = ifelse(
          x$platform == "instagram",
          "Instagram: 2022 March top 300 vs 2024 global top 100",
          "TikTok: 2022 March top 100 vs 2024 global top 100"
        )
      ) %>%
      select(
        platform,
        comparison,
        populated_category,
        group,
        n_2022,
        n_2024,
        cv_2022,
        cv_2024,
        delta_cv,
        p_value
      )
  })
)

print(pvalue_summary)

# -----------------------------
# Save
# -----------------------------

ggsave(
  filename = "delta_cv_instagram300_tiktok100_category_pvalues.png",
  plot = combined_plot,
  width = 8,
  height = 6,
  dpi = 300
)
