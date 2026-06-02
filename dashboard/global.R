suppressPackageStartupMessages({
  library(shiny)
  library(bslib)
  library(shinyWidgets)
  library(shinycssloaders)
  library(plotly)
  library(DT)
  library(visNetwork)
  library(networkD3)
  library(dplyr)
  library(tidyr)
  library(readr)
  library(stringr)
  library(lubridate)
  library(htmltools)
  library(scales)
  library(jsonlite)
})

app_dir <- normalizePath(getwd(), winslash = "/", mustWork = TRUE)
root_dir <- if (basename(app_dir) == "dashboard") normalizePath(file.path(app_dir, ".."), winslash = "/", mustWork = TRUE) else app_dir
processed_dir <- file.path(root_dir, "data", "processed")

read_csv_safe <- function(filename, cols = NULL) {
  path <- file.path(processed_dir, filename)
  if (!file.exists(path)) {
    if (is.null(cols)) return(tibble())
    return(as_tibble(setNames(replicate(length(cols), logical(0), simplify = FALSE), cols)))
  }
  suppressMessages(readr::read_csv(path, show_col_types = FALSE, progress = FALSE))
}

read_parquet_safe <- function(filename) {
  path <- file.path(processed_dir, filename)
  if (!file.exists(path) || !requireNamespace("arrow", quietly = TRUE)) return(tibble())
  arrow::read_parquet(path) |> as_tibble()
}

app_data <- new.env(parent = emptyenv())
app_data$kpis <- read_csv_safe("dashboard_kpis.csv")
app_data$timeseries <- read_csv_safe("dashboard_timeseries.csv")
app_data$topic_year <- read_csv_safe("dashboard_topic_year.csv")
app_data$country_map <- read_csv_safe("dashboard_country_map.csv")
app_data$country_edges <- read_csv_safe("dashboard_country_edges.csv")
app_data$nodes <- read_csv_safe("dashboard_network_nodes.csv")
app_data$edges <- read_csv_safe("dashboard_network_edges.csv")
app_data$code_gap <- read_csv_safe("dashboard_code_gap.csv")
app_data$research_to_code <- read_parquet_safe("research_to_code.parquet")
app_data$papers <- read_parquet_safe("papers.parquet")
app_data$venues <- read_parquet_safe("venues.parquet")
app_data$repos <- read_parquet_safe("repos.parquet")
app_data$contributors <- read_parquet_safe("contributors.parquet")
app_data$paper_code_links <- read_parquet_safe("paper_code_links.parquet")

has_demo_mode <- Sys.getenv("USE_DEMO_DATA", "0") == "1"
available_years <- sort(unique(na.omit(app_data$timeseries$year)))
if (!length(available_years)) available_years <- 2016:2026

safe_choices <- function(x) {
  vals <- sort(unique(na.omit(as.character(x))))
  vals[nzchar(vals)]
}

metric_value <- function(metric) {
  row <- app_data$kpis |> filter(.data$metric == !!metric)
  if (!nrow(row)) return("0")
  value <- suppressWarnings(as.numeric(row$value[1]))
  if (is.na(value)) return(as.character(row$value[1]))
  if (metric == "Research-to-Code Score") percent(value, accuracy = 0.1) else comma(value)
}

empty_state <- function(title, message = "Run the real-data pipeline to populate this view.") {
  div(class = "empty-state", h3(title), p(message))
}

download_button <- function(id, label) {
  downloadButton(id, label, class = "btn-export")
}

filter_dataset <- function(papers, input) {
  if (!nrow(papers)) return(papers)
  out <- papers
  if ("publication_year" %in% names(out)) {
    out <- out |> filter(.data$publication_year >= input$year_range[1], .data$publication_year <= input$year_range[2])
  }
  if (!is.null(input$topic_group) && length(input$topic_group) && "topic_group" %in% names(out)) {
    out <- out |> filter(.data$topic_group %in% input$topic_group)
  }
  if (!is.null(input$venue_quality) && length(input$venue_quality) && "quality_label" %in% names(out)) {
    out <- out |> filter(.data$quality_label %in% input$venue_quality)
  }
  if (!is.null(input$min_citations) && "cited_by_count" %in% names(out)) {
    out <- out |> filter(coalesce(.data$cited_by_count, 0) >= input$min_citations)
  }
  if (!is.null(input$search_box) && nzchar(input$search_box)) {
    pattern <- stringr::fixed(tolower(input$search_box))
    text <- paste(tolower(coalesce(out$title, "")), tolower(coalesce(out$venue_name, "")), tolower(coalesce(out$topic_group, "")))
    out <- out[stringr::str_detect(text, pattern), , drop = FALSE]
  }
  out
}

caption <- function(text) tags$p(class = "chart-caption", text)

card <- function(title, ..., class = "") {
  div(class = paste("panel-card", class), h3(title), ...)
}
