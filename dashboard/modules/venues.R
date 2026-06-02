venues_ui <- function(id) {
  ns <- NS(id)
  div(class = "section-grid",
    card("Venue Quality Summary", withSpinner(plotlyOutput(ns("quality_plot"), height = "330px")), class = "span-4"),
    card("Citation Impact by Quality", withSpinner(plotlyOutput(ns("citation_quality"), height = "330px")), class = "span-4"),
    card("Code Adoption by Quality", withSpinner(plotlyOutput(ns("code_quality"), height = "330px")), class = "span-4"),
    card("Unknown Venue Review", download_button(ns("download_missing_quality"), "Download missing venue quality"), withSpinner(DTOutput(ns("unknown_table"))), class = "span-12")
  )
}

venues_server <- function(id, filtered_papers) {
  moduleServer(id, function(input, output, session) {
    output$quality_plot <- renderPlotly({
      papers <- filtered_papers()
      if (!nrow(papers)) return(plotly_empty())
      q <- papers |> count(quality_label, sort = TRUE)
      plot_ly(q, x = ~quality_label, y = ~n, type = "bar", marker = list(color = "#2563eb")) |> layout(xaxis = list(title = ""), yaxis = list(title = "Papers"))
    })

    output$citation_quality <- renderPlotly({
      papers <- filtered_papers()
      if (!nrow(papers)) return(plotly_empty())
      q <- papers |> group_by(quality_label) |> summarise(citations = sum(cited_by_count, na.rm = TRUE), .groups = "drop")
      plot_ly(q, x = ~quality_label, y = ~citations, type = "bar", marker = list(color = "#64748b")) |> layout(xaxis = list(title = ""), yaxis = list(title = "Citations"))
    })

    output$code_quality <- renderPlotly({
      papers <- filtered_papers()
      ids <- if (nrow(app_data$paper_code_links)) unique(app_data$paper_code_links$work_id) else character()
      if (!nrow(papers)) return(plotly_empty())
      q <- papers |> mutate(has_code = work_id %in% ids) |> group_by(quality_label) |> summarise(score = mean(has_code), .groups = "drop")
      plot_ly(q, x = ~quality_label, y = ~score, type = "bar", marker = list(color = "#16a34a")) |> layout(xaxis = list(title = ""), yaxis = list(title = "Code adoption", tickformat = ".0%"))
    })

    unknown_venues <- reactive({
      papers <- filtered_papers()
      if (!nrow(papers)) return(tibble())
      papers |> filter(is.na(quality_label) | quality_label == "Unknown") |> count(venue_id, venue_name, venue_type, sort = TRUE)
    })

    output$unknown_table <- renderDT({
      datatable(unknown_venues(), options = list(pageLength = 15, scrollX = TRUE), rownames = FALSE)
    })

    output$download_missing_quality <- downloadHandler(
      filename = function() "venue_quality_missing.csv",
      content = function(file) readr::write_csv(unknown_venues(), file)
    )
  })
}
