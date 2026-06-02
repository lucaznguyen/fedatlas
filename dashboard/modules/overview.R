overview_ui <- function(id) {
  ns <- NS(id)
  tagList(
    div(class = "kpi-grid",
      uiOutput(ns("kpi_cards"))
    ),
    br(),
    div(class = "section-grid",
      card("Field Growth", withSpinner(plotlyOutput(ns("growth_plot"), height = "330px")), caption("Annual paper volume, citations, and GitHub-linked papers after the active filters."), class = "span-8"),
      card("Top Topics", withSpinner(plotlyOutput(ns("top_topics"), height = "330px")), class = "span-4"),
      card("Topic-Year Heatmap", withSpinner(plotlyOutput(ns("topic_heatmap"), height = "360px")), class = "span-8"),
      card("Insight Cards", uiOutput(ns("insights")), class = "span-4"),
      card("Top Countries", withSpinner(plotlyOutput(ns("top_countries"), height = "300px")), class = "span-6"),
      card("Top Venues", withSpinner(plotlyOutput(ns("top_venues"), height = "300px")), class = "span-6")
    )
  )
}

overview_server <- function(id, filtered_papers) {
  moduleServer(id, function(input, output, session) {
    output$kpi_cards <- renderUI({
      metrics <- c("Papers", "Authors", "Institutions", "Countries", "Venues", "GitHub Repos", "Total Citations", "Total GitHub Stars", "Research-to-Code Score")
      tagList(lapply(metrics, function(m) div(class = "kpi-card", span(m), strong(metric_value(m)))))
    })

    output$growth_plot <- renderPlotly({
      papers <- filtered_papers()
      if (!nrow(papers)) return(plotly_empty(type = "scatter", mode = "markers") |> layout(title = "No filtered records"))
      ids <- if (nrow(app_data$paper_code_links)) unique(app_data$paper_code_links$work_id) else character()
      ts <- papers |> mutate(has_code = .data$work_id %in% ids) |> group_by(publication_year) |> summarise(
        Papers = n_distinct(work_id),
        Citations = sum(cited_by_count, na.rm = TRUE),
        `GitHub-linked papers` = sum(has_code),
        .groups = "drop"
      )
      plot_ly(ts, x = ~publication_year) |>
        add_lines(y = ~Papers, name = "Papers", line = list(color = "#2563eb")) |>
        add_lines(y = ~`GitHub-linked papers`, name = "GitHub-linked papers", line = list(color = "#16a34a")) |>
        layout(xaxis = list(title = ""), yaxis = list(title = ""), legend = list(orientation = "h"))
    })

    output$top_topics <- renderPlotly({
      papers <- filtered_papers()
      if (!nrow(papers) || !"topic_group" %in% names(papers)) return(plotly_empty())
      top <- papers |> count(topic_group, sort = TRUE) |> slice_head(n = 10)
      plot_ly(top, x = ~n, y = ~reorder(topic_group, n), type = "bar", orientation = "h", marker = list(color = "#2563eb")) |>
        layout(xaxis = list(title = "Papers"), yaxis = list(title = ""))
    })

    output$topic_heatmap <- renderPlotly({
      papers <- filtered_papers()
      if (!nrow(papers)) return(plotly_empty())
      heat <- papers |> count(publication_year, topic_group)
      plot_ly(heat, x = ~publication_year, y = ~topic_group, z = ~n, type = "heatmap", colorscale = "Blues") |>
        layout(xaxis = list(title = ""), yaxis = list(title = ""))
    })

    output$top_countries <- renderPlotly({
      pc <- app_data$country_map
      if (!nrow(pc)) return(plotly_empty())
      top <- pc |> arrange(desc(paper_count)) |> slice_head(n = 10)
      plot_ly(top, x = ~paper_count, y = ~reorder(country_name, paper_count), type = "bar", orientation = "h", marker = list(color = "#38bdf8")) |>
        layout(xaxis = list(title = "Papers"), yaxis = list(title = ""))
    })

    output$top_venues <- renderPlotly({
      papers <- filtered_papers()
      if (!nrow(papers) || !"venue_name" %in% names(papers)) return(plotly_empty())
      top <- papers |> filter(!is.na(venue_name)) |> count(venue_name, sort = TRUE) |> slice_head(n = 10)
      plot_ly(top, x = ~n, y = ~reorder(venue_name, n), type = "bar", orientation = "h", marker = list(color = "#64748b")) |>
        layout(xaxis = list(title = "Papers"), yaxis = list(title = ""))
    })

    output$insights <- renderUI({
      papers <- filtered_papers()
      if (!nrow(papers)) return(empty_state("No insight available"))
      topic_counts <- papers |> count(topic_group, sort = TRUE)
      top_topic <- if (nrow(topic_counts)) topic_counts$topic_group[1] else "Not available"
      country <- if (nrow(app_data$nodes)) {
        row <- app_data$nodes |> filter(node_type == "Country") |> arrange(desc(bridge_score)) |> slice_head(n = 1)
        if (nrow(row)) row$display_label[1] else "Not available"
      } else "Not available"
      rtc <- app_data$research_to_code
      best_rtc <- if (nrow(rtc)) {
        row <- rtc |> filter(group_type == "topic") |> group_by(group_value) |> summarise(score = mean(research_to_code_score, na.rm = TRUE), .groups = "drop") |> arrange(desc(score)) |> slice_head(n = 1)
        if (nrow(row)) row$group_value[1] else "Not available"
      } else "Not available"
      tagList(
        div(class = "kpi-card", span("Most frequent topic"), strong(top_topic)),
        div(class = "kpi-card", span("Top bridge country"), strong(country)),
        div(class = "kpi-card", span("Highest code adoption topic"), strong(best_rtc)),
        div(class = "kpi-card", span("Largest open question"), strong("Uneven code adoption across topics and venues"))
      )
    })
  })
}
