
library(ggplot2)


df <- read.csv('dataset/final.csv', stringsAsFactors = FALSE)
#df <- read.csv('2 - countries and numbers fixed/final.csv', stringsAsFactors = FALSE)

df <- df[df$X_year == '2022',]
df <- df[df$X_month == 'march',]

#build the sets

df <- df[df$X_platform == 'instagram',]

#for each 



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
    title = "P-value vs Sample Size perm test",
    x = "Sample Size",
    y = "P-value"
  ) +
  theme_minimal(base_size = 14)
)
