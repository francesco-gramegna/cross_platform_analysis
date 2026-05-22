
library(ggplot2)
df <- read.csv('dataset/final.csv', stringsAsFactors = FALSE)

df <- df[df$X_platform == 'tiktok',]

df <- df[df$X_year == "2022",]

df <- df[df$X_month == 'march', ]


aa <- df[order(-df$followers), ]
#aa <- aa[1:100,]
ayes <- aa[aa$populated_category != '', ]
print(nrow(ayes))
ano <- aa[aa$populated_category == '', ]
print(nrow(ano))

# 1. Create a logical vector for the Top 100
# TRUE if labeled (ayes), FALSE if empty (ano)
top_100 <- df[order(-df$followers), ][1:100, ]
top_100$is_present <- top_100$populated_category != ''
top_100$index <- 1:100

# 2. Create the binary index plot
print(ggplot(top_100, aes(x = index, y = 1, fill = is_present)) +
  geom_tile() + # Creates a "barcode" effect
  scale_fill_manual(
    values = c("TRUE" = "#2ca02c", "FALSE" = "#d62728"),
    labels = c("TRUE" = "Present (ayes)", "FALSE" = "Missing (ano)"),
    name = "Category Status"
  ) +
  scale_x_continuous(breaks = seq(0, 100, by = 10)) +
  labs(
    title = "Category Presence by Follower Rank (Top 100)",
    subtitle = "Green = Labeled | Red = Empty",
    x = "Follower Rank (1 = Most Followed)",
    y = ""
  ) +
  theme_minimal() +
  theme(
    axis.text.y = element_blank(),
    axis.ticks.y = element_blank(),
    panel.grid.major.y = element_blank(),
    panel.grid.minor.y = element_blank(),
    legend.position = "bottom"
  
	)
)



s1 <- df[order(-df$followers), ]



s1 <- s1[1:100, ]

s2copy <- df[order(-df$followers), ]

pvalues = c()

totest = c(200,300,400,500,600,700,800,900,1000)

for (j in totest){

s2 <- s2copy[100:j, ]




#print(s2[s2$X_country == 'france',][1:30]$name)

print(nrow(s1))


n1 <- nrow(s1)
n2 <- nrow(s2)

a <- rbind(s1, s2)


# Get categorical vectors
x1 <- as.character(s1$populated_category)
x2 <- as.character(s2$populated_category)

# All categories appearing in either sample
categories <- sort(unique(c(x1, x2)))


js_divergence <- function(x1, x2, categories) {

  # Counts
  p_counts <- table(factor(x1, levels = categories))
  q_counts <- table(factor(x2, levels = categories))

  # Probabilities
  p <- p_counts / sum(p_counts)
  q <- q_counts / sum(q_counts)

  # Midpoint distribution
  m <- 0.5 * (p + q)

  # KL divergence helper
  kl_div <- function(a, b) {

    idx <- a > 0

    sum(a[idx] * log2(a[idx] / b[idx]))
  }

  # JS divergence
  js <- 0.5 * kl_div(p, m) +
        0.5 * kl_div(q, m)

  return(js)
}


basejs <- js_divergence(x1, x2, categories)

print(basejs)

numperm<-10000 #number of permutations

jsdiff<-numeric(numperm) #will contain permuted mean difference

ds<-rbind(s1,s2) #combined data set

for(i in 1:numperm) #loop over permutations
{
	a<-sample(n1+n2,n1) #generate permutation sample
	perm1<-ds[a, ] #values in s1
	perm2<-ds[-a, ] #values not in s1
	jsdiff[i]=js_divergence(perm1$populated_category,perm2$populated_category, categories)
}

jsdiff<-sort(jsdiff,decreasing=T) #sort meandiff values
#hist(jsdiff)


p_two_sided <- mean(jsdiff >= basejs)
print(p_two_sided)

pvalues  <- c(pvalues, p_two_sided)
}

df <- data.frame(
  sample_size = totest,
  pvalue = pvalues
)

print(nrow(df))


print(ggplot(df, aes(x = sample_size, y = pvalue)) +
  geom_line(color = "steelblue", linewidth = 1) +
  geom_point(color = "steelblue", size = 3) +
  geom_hline(yintercept = 0.05,
             linetype = "dashed",
             color = "red") +
  labs(
    title = "P-value vs Sample Size perm. test. TikTok",
    x = "Sample Size",
    y = "P-value"
  ) +
  theme_minimal(base_size = 14)
)


#plot(before$populated_category != '')



