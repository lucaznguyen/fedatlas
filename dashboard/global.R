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
app_data$country_centroids <- read_csv_safe("dashboard_country_centroids.csv")
app_data$nodes <- read_csv_safe("dashboard_network_nodes.csv")
app_data$edges <- read_csv_safe("dashboard_network_edges.csv")
app_data$code_gap <- read_csv_safe("dashboard_code_gap.csv")
app_data$research_to_code <- read_parquet_safe("research_to_code.parquet")
app_data$papers <- read_parquet_safe("papers.parquet")
app_data$venues <- read_parquet_safe("venues.parquet")
app_data$repos <- read_parquet_safe("repos.parquet")
app_data$contributors <- read_parquet_safe("contributors.parquet")
app_data$paper_code_links <- read_parquet_safe("paper_code_links.parquet")
app_data$paper_countries <- read_parquet_safe("paper_countries.parquet")
app_data$repo_contributors <- read_parquet_safe("repo_contributors.parquet")

has_demo_mode <- Sys.getenv("USE_DEMO_DATA", "0") == "1"
available_years <- sort(unique(na.omit(app_data$timeseries$year)))
if (!length(available_years)) available_years <- 2016:2026

safe_choices <- function(x) {
  vals <- sort(unique(na.omit(as.character(x))))
  vals[nzchar(vals)]
}

paper_count_colorscale <- list(
  c(0.00, "#eff6ff"),
  c(0.25, "#bfdbfe"),
  c(0.50, "#60a5fa"),
  c(0.75, "#2563eb"),
  c(1.00, "#0b1f75")
)

as_number <- function(x, default = 0) {
  out <- suppressWarnings(as.numeric(x))
  out[is.na(out)] <- default
  out
}

as_flag <- function(x) {
  if (is.logical(x)) return(replace_na(x, FALSE))
  tolower(as.character(x)) %in% c("true", "t", "1", "yes", "y")
}

empty_dt <- function(message) {
  datatable(tibble(message = message), options = list(dom = "t", pageLength = 1), rownames = FALSE)
}

topic_heatmap_plot <- function(papers, max_topics = 18) {
  if (!nrow(papers) || !all(c("publication_year", "topic_group") %in% names(papers))) return(plotly_empty())
  heat <- papers |>
    mutate(
      publication_year = as.integer(as_number(.data$publication_year, NA_real_)),
      topic_group = coalesce(as.character(.data$topic_group), "Unassigned")
    ) |>
    filter(!is.na(.data$publication_year), nzchar(.data$topic_group)) |>
    count(.data$publication_year, .data$topic_group, name = "papers")
  if (!nrow(heat)) return(plotly_empty())

  top_topics <- heat |>
    group_by(.data$topic_group) |>
    summarise(total = sum(.data$papers, na.rm = TRUE), .groups = "drop") |>
    arrange(desc(.data$total), .data$topic_group) |>
    slice_head(n = max_topics)
  years <- seq(min(heat$publication_year, na.rm = TRUE), max(heat$publication_year, na.rm = TRUE))
  topic_order <- rev(top_topics$topic_group)

  heat_wide <- heat |>
    filter(.data$topic_group %in% top_topics$topic_group) |>
    mutate(topic_group = factor(.data$topic_group, levels = topic_order)) |>
    complete(publication_year = years, topic_group = factor(topic_order, levels = topic_order), fill = list(papers = 0)) |>
    arrange(.data$topic_group, .data$publication_year) |>
    pivot_wider(names_from = .data$publication_year, values_from = .data$papers, values_fill = 0)

  z <- as.matrix(heat_wide[, as.character(years), drop = FALSE])
  storage.mode(z) <- "numeric"
  plot_ly(
    x = years,
    y = as.character(heat_wide$topic_group),
    z = z,
    type = "heatmap",
    colorscale = paper_count_colorscale,
    reversescale = FALSE,
    colorbar = list(title = "Papers"),
    hovertemplate = "Year: %{x}<br>Topic: %{y}<br>Papers: %{z}<extra></extra>"
  ) |>
    layout(xaxis = list(title = ""), yaxis = list(title = ""))
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
  if (!is.null(input$venue_type) && length(input$venue_type) && "venue_type" %in% names(out)) {
    out <- out |> filter(.data$venue_type %in% input$venue_type)
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
