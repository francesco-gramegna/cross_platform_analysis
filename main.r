path <- "crude_dataset/kaggle_2022"

files <- list.files(path, full.names = TRUE)

for (f in files) {
  name <- basename(f)                 # file name → variable name
  df <- read.csv(f, stringsAsFactors = FALSE)

  assign(name, df, envir = .GlobalEnv)
}

loaded <- ls(pattern = "instagram|tiktok|youtube")

print(unique(get(loaded[2])$category_1))

for (name in loaded) {
  cat("\n---", name, "---\n")
  df <- get(name)
  print(unique(df$category_1))
}

