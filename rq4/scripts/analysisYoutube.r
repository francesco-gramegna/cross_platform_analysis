df <- read.csv('dataset/final.csv', stringsAsFactors = FALSE)


#print(unique(df$populated_category))

 #[1] "Sports"         "Beauty&Fashion" "Music"          "Lifestyle"     
 #[5] "Entertainment"  "Knowledge&Info" "Tech&Gaming"    ""              
 #[9] "Other"          "UNMAPPED"      


df <- df[df$X_platform == 'youtube',]

ai_susceptible <- c("Knowledge&Info", "Entertainment")

unsure <- c('Tech&Gaming', 'Beauty&Fashion', "Lifestyle")

human <- c('Sports', 'Music') #for music

before <- df[df$X_year == "2022",]
before <- before[before$X_month == "march", ]
#before <- before[order(-before$followers), ]
#before <- before[1:100, ]
before <- before[before$populated_category != '', ]

after <- df[df$X_year == "2026",]


feat = 'er_pct'


# 1. Setup Groups
groups <- list(ai = ai_susceptible, human = human)

# Function to calculate CV: (sd / mean)
calc_cv <- function(x) sd(x, na.rm = TRUE) / mean(x, na.rm = TRUE)

# 2. Extract CVs for 2022 and 2024
results <- lapply(groups, function(cats) {
  cv_2022 <- calc_cv(before[before$populated_category %in% cats, "er_pct"])
  cv_2024 <- calc_cv(after[after$populated_category %in% cats, "er_pct"])
  return(list(cv22 = cv_2022, cv24 = cv_2024, diff = cv_2024 - cv_2022))
})

# 3. Bootstrap Test for AI-Susceptible Group
ai_2022 <- before[before$populated_category %in% ai_susceptible, "er_pct"]
ai_2024 <- after[after$populated_category %in% ai_susceptible, "er_pct"]

n_boot <- 1000
boot_diffs <- replicate(n_boot, {
  # Resample with replacement
  s22 <- sample(ai_2022, replace = TRUE)
  s24 <- sample(ai_2024, replace = TRUE)
  calc_cv(s24) - calc_cv(s22)
})

# 4. Results
p_value <- mean(boot_diffs >= 0) # Probability that diff is NOT negative

print(results)
cat("Bootstrap P-value for AI Convergence:", p_value, "\n")


