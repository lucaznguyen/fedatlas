repos_ui <- function(id) {
  ns <- NS(id)
  div(class = "section-grid",
    card("Repository Leaderboard", withSpinner(DTOutput(ns("repo_table"))), class = "span-8"),
    card("Language Distribution", withSpinner(plotlyOutput(ns("language_plot"), height = "360px")), class = "span-4"),
    card("Repository Activity", withSpinner(plotlyOutput(ns("activity_plot"), height = "320px")), class = "span-6"),
    card("Contributor Leaderboard", withSpinner(DTOutput(ns("contrib_table"))), class = "span-6")
  )
}

repos_server <- function(id, filtered_papers) {
  moduleServer(id, function(input, output, session) {
    output$repo_table <- renderDT({
      repos <- app_data$repos
      if (!nrow(repos)) return(datatable(tibble()))
      repos |> filter(coalesce(stargazers_count, 0) >= input$min_stars) |> arrange(desc(code_score), desc(stargazers_count)) |>
        select(repo_full_name, description, stargazers_count, forks_count, language, license, pushed_at, code_score, repo_url) |>
        datatable(options = list(pageLength = 15, scrollX = TRUE), rownames = FALSE)
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
      if (!nrow(app_data$contributors)) return(datatable(tibble()))
      app_data$contributors |> select(login, type, html_url) |> datatable(options = list(pageLength = 15, scrollX = TRUE), rownames = FALSE)
    })
  })
}
