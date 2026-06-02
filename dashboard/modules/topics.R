topics_ui <- function(id) {
  ns <- NS(id)
  div(class = "section-grid",
    card("Topic-Year Heatmap", withSpinner(plotlyOutput(ns("topic_heatmap"), height = "430px")), class = "span-8"),
    card("Rising Topics", withSpinner(DTOutput(ns("rising_topics"))), class = "span-4"),
    card("Topic Group Trend", withSpinner(plotlyOutput(ns("area_chart"), height = "360px")), class = "span-12"),
    card("Topic Detail", withSpinner(DTOutput(ns("topic_detail"))), class = "span-12")
  )
}

topics_server <- function(id, filtered_papers) {
  moduleServer(id, function(input, output, session) {
    output$topic_heatmap <- renderPlotly({
      papers <- filtered_papers()
      if (!nrow(papers)) return(plotly_empty())
      heat <- papers |> count(publication_year, topic_group)
      plot_ly(heat, x = ~publication_year, y = ~topic_group, z = ~n, type = "heatmap", colorscale = "Blues") |>
        layout(xaxis = list(title = ""), yaxis = list(title = ""))
    })

    output$area_chart <- renderPlotly({
      papers <- filtered_papers()
      if (!nrow(papers)) return(plotly_empty())
      trend <- papers |> count(publication_year, topic_group)
      plot_ly(trend, x = ~publication_year, y = ~n, color = ~topic_group, type = "scatter", mode = "lines", stackgroup = "one") |>
        layout(xaxis = list(title = ""), yaxis = list(title = "Papers"), legend = list(orientation = "h"))
    })

    output$rising_topics <- renderDT({
      papers <- filtered_papers()
      if (!nrow(papers)) return(datatable(tibble()))
      min_year <- min(papers$publication_year, na.rm = TRUE)
      max_year <- max(papers$publication_year, na.rm = TRUE)
      rising <- papers |>
        filter(publication_year %in% c(min_year, max_year)) |>
        count(topic_group, publication_year) |>
        pivot_wider(names_from = publication_year, values_from = n, values_fill = 0)
      if (ncol(rising) >= 3) {
        rising$growth <- rising[[as.character(max_year)]] - rising[[as.character(min_year)]]
      } else rising$growth <- 0
      rising |> arrange(desc(growth)) |> datatable(options = list(pageLength = 10, scrollX = TRUE), rownames = FALSE)
    })

    output$topic_detail <- renderDT({
      papers <- filtered_papers()
      if (!nrow(papers)) return(datatable(tibble()))
      papers |> group_by(topic_group) |> summarise(
        papers = n_distinct(work_id),
        citations = sum(cited_by_count, na.rm = TRUE),
        top_venue = names(sort(table(venue_name), decreasing = TRUE))[1],
        representative_paper = title[which.max(coalesce(cited_by_count, 0))],
        .groups = "drop"
      ) |> arrange(desc(papers)) |> datatable(options = list(pageLength = 12, scrollX = TRUE), rownames = FALSE)
    })
  })
}
