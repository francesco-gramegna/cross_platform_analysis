
predata_path <- "3 - handles merging/preprocessedData.csv"
data_path <- "3 - handles merging/finalData.csv"


data <- read.csv(data_path, header=TRUE, stringsAsFactors=FALSE)
library(dplyr)
library(tidyr)
library(ggplot2)

plot_data <- data %>%
  pivot_longer(
    cols = c(category_unified, populated_category),
    names_to = "type",
    values_to = "value"
  ) %>%
  group_by(X_platform, type) %>%
  mutate(total_platform_type = n()) %>%
  group_by(X_platform, type, X_year) %>%
  summarise(
    non_empty = sum(value != ""),
    total_platform_type = first(total_platform_type),
    pct = non_empty / total_platform_type * 100,
    .groups = "drop"
  )

plot_data$X_year <- factor(plot_data$X_year, levels = c(2022, 2024, 2026))


diff_data <- plot_data %>%
  group_by(X_platform, type) %>%
  summarise(
    total_pct = sum(pct),
    .groups = "drop"
  ) %>%
  pivot_wider(
    names_from = type,
    values_from = total_pct
  ) %>%
  mutate(
diff_pct = (populated_category - category_unified) / category_unified * 100
  )

aaaa <- plot_data %>%
  group_by(X_platform, type) %>%
  summarise(
    total_pct = sum(pct),
    .groups = "drop"
  ) %>%
  pivot_wider(
    names_from = type,
    values_from = total_pct
  ) %>%
  mutate(
    diff_pct = category_unified
  )




diff_plot <- diff_data %>%
  mutate(type = "populated_category")

diff_plot1 <- aaaa %>%
  mutate(type = "category_unified")



p <- ggplot(plot_data, aes(x = type, y = pct, fill = X_year)) +
  geom_bar(stat = "identity", position = "stack") +
  facet_wrap(~ X_platform) +

  scale_x_discrete(labels = c(
    "category_unified" = "Original",
    "populated_category" = "Populated"
  )) +
  scale_y_continuous(limits = c(0, 110)) +  # little space for labels
  scale_fill_manual(
    values = c(
      "2022" = "#66c2a5",
      "2024" = "#fc8d62",
      "2026" = "#8da0cb"
    )
  ) +
  geom_text(
    data = diff_plot1,
    aes(
      x = type,
      y = category_unified,
      label = paste0("", round(diff_pct, 1), "%")
    ),
    inherit.aes = FALSE,
    vjust = -0.5,
    size = 5.35
  ) +
  geom_text(
    data = diff_plot,
    aes(
      x = type,
      y = populated_category,

label = paste0(round(populated_category, 1), "% (+", round(diff_pct, 1), "%)")
    ),
    inherit.aes = FALSE,
    vjust = -0.5,
    size = 5.35
  ) +
  ylab("Per platform percentage of non-null category") +
  xlab("") +
  theme(
    axis.text.x = element_text(angle = 45, hjust = 1, size = 15),
    axis.text.y = element_text(size = 15),
    axis.title = element_text(size = 17),
    strip.text = element_text(size = 17),
    legend.text = element_text(size = 15),
    legend.title = element_text(size = 16),
    legend.position = c(0.88, 0.88),
    legend.background = element_rect(fill = "white", color = "grey70")
  )



ggsave("plot.png", plot = p, width = 11, height = 8)

print(p)



totals_per_category <- category_year_plot_data %>%
  group_by(populated_category) %>%
  summarise(total_pct = sum(pct), .groups = "drop")

category_year_plot_data <- data %>%
  filter(populated_category != "") %>%
  mutate(
    artificial = ifelse(category_unified == "", "Artificially populated", "Already present")
  ) %>%
  group_by(populated_category, X_year, artificial) %>%
  summarise(n = n(), .groups = "drop") %>%
  mutate(
    pct = n / nrow(data %>% filter(populated_category != "")) * 100
  )

category_year_plot_data$X_year <- factor(category_year_plot_data$X_year, levels = c(2022, 2024, 2026))
category_year_plot_data$artificial <- factor(
  category_year_plot_data$artificial,
  levels = c("Already present", "Artificially populated")
)

p_categories_year <- ggplot(
  category_year_plot_data,
  aes(
    x = reorder(populated_category, pct, sum),
    y = pct,
    fill = X_year,
    alpha = artificial
  )
) +
  geom_bar(stat = "identity", position = "stack") +
  coord_flip() +
 geom_text(
    data = totals_per_category,
    aes(
      x = populated_category,
      y = total_pct,
      label = paste0(round(total_pct, 1), "%")
    ),
    inherit.aes = FALSE,
    hjust = -0.1,
    size = 4.5
  ) +
  scale_y_continuous(expand = expansion(mult = c(0, 0.15))) +
  scale_fill_manual(
    values = c(
      "2022" = "#66c2a5",
      "2024" = "#fc8d62",
      "2026" = "#8da0cb"
    )
  ) +
  scale_alpha_manual(
    values = c(
      "Already present" = 0.65,
      "Artificially populated" = 1
    )
  ) +
  ylab("Percentage of total populated categories") +
  xlab("Populated category") +
  labs(fill = "Year", alpha = "Source") +
  theme(
    axis.text.x = element_text(size = 14),
    axis.text.y = element_text(size = 14),
    axis.title = element_text(size = 16),
    legend.text = element_text(size = 12),
    legend.title = element_text(size = 14),
		legend.position = c(0.9,0.2)
  )

ggsave("populated_category_by_year_artificial.png", plot = p_categories_year, width = 9, height = 8)

print(p_categories_year)


#....

#we now peroform the permutation test

clean <- data[data$category_unified != "" & data$populated_category != "", ]
artificial <- data[data$category_unified == "" & data$populated_category != "", ]

l1_distance <- function(df1, df2) {
  counts1 <- table(df1$populated_category)
  counts2 <- table(df2$populated_category)
  
  all_cats <- union(names(counts1), names(counts2))
  
  counts1 <- counts1[all_cats]
  counts2 <- counts2[all_cats]
  
  counts1[is.na(counts1)] <- 0
  counts2[is.na(counts2)] <- 0
  
  prob1 <- counts1 / sum(counts1)
  prob2 <- counts2 / sum(counts2)
  
  sum(abs(prob1 - prob2))
}

observed_diff <- l1_distance(clean, artificial)

n1 <- nrow(clean)
n2 <- nrow(artificial)

numperm <- 1000
perm_diff <- numeric(numperm)

ds <- rbind(clean, artificial)

set.seed(1)

for (i in 1:numperm) {
  s1 <- sample(n1 + n2, n1)
  
  perm1 <- ds[s1, ]
  perm2 <- ds[-s1, ]
  
  perm_diff[i] <- l1_distance(perm1, perm2)
}

hist(perm_diff)
abline(v = observed_diff, col = "red", lwd = 3)

meandiffobs <- observed_diff   # your observed L1 distance

upperpval <- length(perm_diff[perm_diff >= meandiffobs]) / numperm
lowerpval <- length(perm_diff[perm_diff <= meandiffobs]) / numperm

# One-sided (choose depending on hypothesis)
pval_one_sided <- upperpval   # usually this one (testing "difference is large")

# Two-sided
pval_two_sided <- 2 * min(upperpval, lowerpval)

print(pval_one_sided)
print(pval_two_sided)
