df <- read.csv('dataset/final.csv', stringsAsFactors = FALSE)
#df <- read.csv('2 - countries and numbers fixed/final.csv', stringsAsFactors = FALSE)

df <- df[df$X_year == '2024',]

#build the sets

df <- df[df$X_platform == 'instagram',]

s1 <- df[df$X_is_global == 'True',]


#for each 



#s2 <- df[df$X_is_global == 'False', ]

#s2 <- s2[order(-s2$followers), ]

#s2 <- s2[1:600, ]

s2 <- df[df$X_is_global == "False", ]

# sort by followers descending
s2 <- s2[order(-s2$followers), ]

# count how many rows per country exist in full s2
country_counts <- table(s2$X_country)

selected <- c()
remaining_counts <- country_counts

maxb <- 3
b <- 0
for (i in 1:nrow(s2)) {

  country <- s2$X_country[i]

  # simulate removing this row
  remaining_counts[country] <- remaining_counts[country] - 1

  # if this would make the country disappear, STOP before adding it
  if (remaining_counts[country] == 0) {
		print(country)
		print('TOO MANY')
		print(i)
		b <- b+1
		if(b >= maxb){
			break
		}
    #break
  }

  selected <- c(selected, i)
}

s2_final <- s2[selected, ]

print(nrow(s2_final))

print(nrow(s2))

s2 <- s2_final[1:600,]

#print(s2[s2$X_country == 'france',][1:30]$name)


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



