library(dplyr)
library(tidyr)
library(ggplot2)



data_path <- "3 - handles merging/finalData.csv"


library(patchwork)

cluster_summary <- data %>%
  group_by(uniqueId) %>%
  summarise(
    cluster_size = n(),
    n_platforms = n_distinct(X_platform),
    .groups = "drop"
  )

cluster_counts <- cluster_summary %>%
  count(cluster_size, name = "total_count")

cluster_props <- cluster_summary %>%
  count(cluster_size, n_platforms, name = "count") %>%
  group_by(cluster_size) %>%
  mutate(prop = count / sum(count)) %>%
  ungroup()

p_total <- ggplot(cluster_counts, aes(x = factor(cluster_size), y = total_count)) +
  geom_col(fill = "grey70") +
  geom_text(
    aes(label = total_count),
    vjust = -0.3,
    size = 4
  ) +
  scale_y_log10() +
  xlab("") +
  ylab("Number of clusters\n(log scale)") +
  theme(
    axis.text.x = element_blank(),
    axis.ticks.x = element_blank(),
    axis.text.y = element_text(size = 13),
    axis.title.y = element_text(size = 15)
  )

p_prop <- ggplot(cluster_props, aes(x = factor(cluster_size), y = prop, fill = factor(n_platforms))) +
  geom_col(position = "fill") +
  scale_y_continuous(labels = scales::percent) +
  scale_fill_manual(
    values = c(
      "1" = "#a6cee3",
      "2" = "#1f78b4",
      "3" = "#b2df8a"
    ),
    name = "Number of platforms"
  ) +
  xlab("Cluster size") +
  ylab("Platform-span proportion") +
  theme(
    axis.text.x = element_text(size = 13),
    axis.text.y = element_text(size = 13),
    axis.title = element_text(size = 15),
    legend.text = element_text(size = 13),
    legend.title = element_text(size = 14),
		legend.position = c(0.9,2.8)
  )

p_cluster <- p_total / p_prop + plot_layout(heights = c(2, 1))

ggsave("cluster_size_platforms_clean.png", plot = p_cluster, width = 12, height = 8)

print(p_cluster)
