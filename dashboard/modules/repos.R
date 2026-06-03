repos_ui <- function(id) {
  ns <- NS(id)
  div(class = "section-grid",
    card("Repository Leaderboard", withSpinner(DTOutput(ns("repo_table"))), class = "span-8"),
    card("Language Distribution", withSpinner(plotlyOutput(ns("language_plot"), height = "360px")), class = "span-4"),
    card("Repository Activity", withSpinner(plotlyOutput(ns("activity_plot"), height = "320px")), class = "span-6"),
    card("Contributor Leaderboard", withSpinner(DTOutput(ns("contrib_table"))), class = "span-6")
  )
}

repos_server <- function(id, filtered_papers, min_stars = reactive(0)) {
  moduleServer(id, function(input, output, session) {
    output$repo_table <- renderDT({
      repos <- app_data$repos
      if (!nrow(repos)) return(empty_dt("No GitHub repositories were found in the processed data."))
      papers <- filtered_papers()
      links <- app_data$paper_code_links
      if (nrow(papers) && nrow(links)) {
        visible_repos <- links |>
          filter(.data$work_id %in% papers$work_id) |>
          transmute(repo_full_name = paste(.data$repo_owner, .data$repo_name, sep = "/")) |>
          distinct()
        if (nrow(visible_repos)) repos <- repos |> filter(.data$repo_full_name %in% visible_repos$repo_full_name)
      }
      min_star_value <- suppressWarnings(as.numeric(min_stars()))
      if (is.na(min_star_value)) min_star_value <- 0
      table_data <- repos |>
        mutate(
          stargazers_count = as_number(.data$stargazers_count, 0),
          forks_count = as_number(.data$forks_count, 0),
          code_score = as_number(.data$code_score, 0),
          language = coalesce(as.character(.data$language), "Unknown"),
          license = coalesce(as.character(.data$license), "Unknown"),
          pushed_at = as.character(.data$pushed_at),
          description = coalesce(as.character(.data$description), "")
        ) |>
        filter(.data$stargazers_count >= min_star_value) |>
        arrange(desc(.data$code_score), desc(.data$stargazers_count)) |>
        select(any_of(c("repo_full_name", "description", "stargazers_count", "forks_count", "language", "license", "pushed_at", "code_score", "repo_url"))) |>
        slice_head(n = 100)
      if (!nrow(table_data)) return(empty_dt("No repositories match the active filters."))
      datatable(table_data, options = list(pageLength = 15, scrollX = TRUE), rownames = FALSE)
    })

    output$language_plot <- renderPlotly({
      repos <- app_data$repos
      if (!nrow(repos) || !"language" %in% names(repos)) return(plotly_empty())
      lang <- repos |> filter(!is.na(language), nzchar(language)) |> count(language, sort = TRUE) |> slice_head(n = 12)
      plot_ly(lang, labels = ~language, values = ~n, type = "pie", textposition = "inside")
    })

    output$activity_plot <- renderPlotly({
      repos <- app_data$repos
      if (!nrow(repos) || !"pushed_at" %in% names(repos)) return(plotly_empty())
      act <- repos |> mutate(pushed_year = lubridate::year(lubridate::ymd_hms(pushed_at, quiet = TRUE))) |> filter(!is.na(pushed_year)) |> count(pushed_year)
      plot_ly(act, x = ~pushed_year, y = ~n, type = "bar", marker = list(color = "#2563eb")) |> layout(xaxis = list(title = ""), yaxis = list(title = "Repos pushed"))
    })

    output$contrib_table <- renderDT({
      rc <- app_data$repo_contributors
      contributors <- app_data$contributors
      if (!nrow(rc)) {
        return(empty_dt("Contributor metadata is not available yet. Re-run the GitHub enrichment step with GITHUB_TOKEN to populate this leaderboard."))
      }
      leaderboard <- rc |>
        mutate(
          login = coalesce(as.character(.data$login), as.character(.data$contributor_id)),
          contributions = as_number(.data$contributions, 0)
        ) |>
        group_by(.data$login) |>
        summarise(
          repositories = n_distinct(.data$repo_full_name),
          contributions = sum(.data$contributions, na.rm = TRUE),
          .groups = "drop"
        )
      if (nrow(contributors)) {
        leaderboard <- leaderboard |>
          left_join(contributors |> select(login, type, html_url), by = "login")
      }
      leaderboard |>
        arrange(desc(.data$contributions), desc(.data$repositories), .data$login) |>
        slice_head(n = 100) |>
        datatable(options = list(pageLength = 15, scrollX = TRUE), rownames = FALSE)
    })
  })
}
