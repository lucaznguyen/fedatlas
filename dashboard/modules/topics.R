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
      topic_heatmap_plot(papers, max_topics = 18)
    })

    output$area_chart <- renderPlotly({
      papers <- filtered_papers()
      if (!nrow(papers) || !all(c("publication_year", "topic_group") %in% names(papers))) return(plotly_empty())
      trend <- papers |>
        mutate(
          publication_year = as.integer(as_number(.data$publication_year, NA_real_)),
          topic_group = coalesce(as.character(.data$topic_group), "Unassigned")
        ) |>
        filter(!is.na(.data$publication_year), nzchar(.data$topic_group)) |>
        count(.data$publication_year, .data$topic_group, name = "papers")
      if (!nrow(trend)) return(plotly_empty())

      top_topics <- trend |>
        group_by(.data$topic_group) |>
        summarise(total = sum(.data$papers, na.rm = TRUE), .groups = "drop") |>
        arrange(desc(.data$total)) |>
        slice_head(n = 12)
      years <- seq(min(trend$publication_year, na.rm = TRUE), max(trend$publication_year, na.rm = TRUE))
      trend <- trend |>
        filter(.data$topic_group %in% top_topics$topic_group) |>
        complete(publication_year = years, topic_group = top_topics$topic_group, fill = list(papers = 0))

      p <- plot_ly()
      for (topic in top_topics$topic_group) {
        topic_rows <- trend |> filter(.data$topic_group == !!topic)
        p <- p |> add_trace(
          data = topic_rows,
          x = ~publication_year,
          y = ~papers,
          name = topic,
          type = "scatter",
          mode = "lines",
          stackgroup = "one",
          hovertemplate = paste0(topic, "<br>Year: %{x}<br>Papers: %{y}<extra></extra>")
        )
      }
      p |> layout(xaxis = list(title = ""), yaxis = list(title = "Papers"), legend = list(orientation = "h"))
    })

    output$rising_topics <- renderDT({
      papers <- filtered_papers()
      if (!nrow(papers) || !all(c("publication_year", "topic_group") %in% names(papers))) return(empty_dt("No topic records match the active filters."))
      topic_year <- papers |>
        mutate(
          publication_year = as.integer(as_number(.data$publication_year, NA_real_)),
          topic_group = coalesce(as.character(.data$topic_group), "Unassigned")
        ) |>
        filter(!is.na(.data$publication_year), nzchar(.data$topic_group)) |>
        count(.data$topic_group, .data$publication_year, name = "papers")
      if (!nrow(topic_year)) return(empty_dt("No topic records match the active filters."))

      min_year <- min(topic_year$publication_year, na.rm = TRUE)
      max_year <- max(topic_year$publication_year, na.rm = TRUE)
      rising <- topic_year |>
        filter(.data$publication_year %in% c(min_year, max_year)) |>
        pivot_wider(names_from = .data$publication_year, values_from = .data$papers, values_fill = 0)
      if (as.character(min_year) %in% names(rising) && as.character(max_year) %in% names(rising)) {
        rising$growth <- rising[[as.character(max_year)]] - rising[[as.character(min_year)]]
      } else {
        rising$growth <- 0
      }
      rising |>
        arrange(desc(.data$growth), .data$topic_group) |>
        datatable(options = list(pageLength = 10, scrollX = TRUE), rownames = FALSE)
    })

    output$topic_detail <- renderDT({
      papers <- filtered_papers()
      if (!nrow(papers)) return(empty_dt("No topic records match the active filters."))
      papers |> group_by(topic_group) |> summarise(
        papers = n_distinct(work_id),
        citations = sum(as_number(cited_by_count, 0), na.rm = TRUE),
        top_venue = first(names(sort(table(na.omit(venue_name)), decreasing = TRUE)), default = NA_character_),
        representative_paper = title[which.max(as_number(cited_by_count, 0))],
        .groups = "drop"
      ) |> arrange(desc(papers)) |> datatable(options = list(pageLength = 12, scrollX = TRUE), rownames = FALSE)
    })
  })
}
