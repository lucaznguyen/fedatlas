#!/usr/bin/env Rscript

`%||%` <- function(x, y) if (is.null(x) || !length(x) || is.na(x)) y else x

required_packages <- c("rsconnect")
missing_packages <- required_packages[!vapply(required_packages, requireNamespace, logical(1), quietly = TRUE)]
if (length(missing_packages)) {
  install.packages(missing_packages, repos = "https://cloud.r-project.org")
}

args <- commandArgs(FALSE)
file_arg <- sub("^--file=", "", args[grepl("^--file=", args)][1] %||% "scripts/09_deploy_shinyapps.R")
root <- normalizePath(file.path(dirname(file_arg), ".."), mustWork = TRUE)
dashboard_dir <- file.path(root, "dashboard")
processed_dir <- file.path(root, "data", "processed")

if (!dir.exists(processed_dir)) {
  stop("Missing data/processed. Run `make build` before deploying.", call. = FALSE)
}

account <- Sys.getenv("SHINYAPPS_ACCOUNT")
token <- Sys.getenv("SHINYAPPS_TOKEN")
secret <- Sys.getenv("SHINYAPPS_SECRET")
app_name <- Sys.getenv("SHINYAPPS_APP_NAME", "fedatlas")

saved_accounts <- rsconnect::accounts()
if (!nzchar(account) && nrow(saved_accounts) == 1) {
  account <- saved_accounts$name[1]
}

has_env_credentials <- nzchar(account) && nzchar(token) && nzchar(secret)
has_saved_credentials <- nzchar(account) && nrow(saved_accounts) && account %in% saved_accounts$name

if (!has_env_credentials && !has_saved_credentials) {
  stop(
    paste(
      "Missing shinyapps.io credentials.",
      "Either run rsconnect::setAccountInfo(...) once or set SHINYAPPS_ACCOUNT, SHINYAPPS_TOKEN, and SHINYAPPS_SECRET.",
      "Get token/secret from shinyapps.io > Account > Tokens.",
      sep = "\n"
    ),
    call. = FALSE
  )
}

bundle_dir <- file.path(tempdir(), paste0("fedatlas-shinyapps-", format(Sys.time(), "%Y%m%d%H%M%S")))
dir.create(bundle_dir, recursive = TRUE, showWarnings = FALSE)

copy_dir <- function(from, to) {
  if (dir.exists(to)) unlink(to, recursive = TRUE, force = TRUE)
  dir.create(dirname(to), recursive = TRUE, showWarnings = FALSE)
  file.copy(from, dirname(to), recursive = TRUE, copy.date = TRUE)
}

file.copy(file.path(dashboard_dir, "app.R"), bundle_dir, overwrite = TRUE)
file.copy(file.path(dashboard_dir, "global.R"), bundle_dir, overwrite = TRUE)
copy_dir(file.path(dashboard_dir, "modules"), file.path(bundle_dir, "modules"))
copy_dir(file.path(dashboard_dir, "www"), file.path(bundle_dir, "www"))

bundle_processed <- file.path(bundle_dir, "data", "processed")
dir.create(bundle_processed, recursive = TRUE, showWarnings = FALSE)
needed_patterns <- c(
  "^dashboard_.*\\.csv$",
  "^nodes\\.csv$",
  "^edges\\.csv$",
  ".*\\.parquet$"
)
processed_files <- list.files(processed_dir, full.names = TRUE)
keep <- Reduce(`|`, lapply(needed_patterns, function(pattern) grepl(pattern, basename(processed_files))))
file.copy(processed_files[keep], bundle_processed, overwrite = TRUE)

if (has_env_credentials) {
  rsconnect::setAccountInfo(name = account, token = token, secret = secret)
}
rsconnect::deployApp(
  appDir = bundle_dir,
  account = account,
  appName = app_name,
  appTitle = "FedAtlas",
  forceUpdate = TRUE
)
