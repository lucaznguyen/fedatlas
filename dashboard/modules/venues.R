venues_ui <- function(id) {
  ns <- NS(id)
  div(class = "section-grid",
    card("Venue Type Summary", withSpinner(plotlyOutput(ns("type_plot"), height = "330px")), class = "span-4"),
    card("Citation Impact by Venue Type", withSpinner(plotlyOutput(ns("citation_type"), height = "330px")), class = "span-4"),
    card("Code Adoption by Venue Type", withSpinner(plotlyOutput(ns("code_type"), height = "330px")), class = "span-4"),
    card("Venue Metadata Review", download_button(ns("download_venue_metadata"), "Download venue metadata"), withSpinner(DTOutput(ns("venue_table"))), class = "span-12")
  )
}

venues_server <- function(id, filtered_papers) {
  moduleServer(id, function(input, output, session) {
    venue_type_data <- function(papers) {
      papers |>
        mutate(
          venue_name = coalesce(as.character(.data$venue_name), "Missing venue"),
          venue_type_raw = str_to_lower(coalesce(as.character(.data$venue_type), "")),
          venue_group = case_when(
            .data$venue_type_raw == "journal" ~ "Journal",
            .data$venue_type_raw == "conference" ~ "Conference",
            .data$venue_type_raw == "repository" ~ "Preprint / Repository",
            .data$venue_type_raw %in% c("book series", "ebook platform") ~ "Book / Series",
            nzchar(.data$venue_type_raw) ~ str_to_title(.data$venue_type_raw),
            TRUE ~ "Missing venue"
          )
        )
    }

    output$type_plot <- renderPlotly({
      papers <- filtered_papers()
      if (!nrow(papers)) return(plotly_empty())
      q <- venue_type_data(papers) |> count(venue_group, sort = TRUE)
      plot_ly(q, x = ~venue_group, y = ~n, type = "bar", marker = list(color = ~n, colorscale = paper_count_colorscale, reversescale = FALSE, showscale = FALSE)) |> layout(xaxis = list(title = ""), yaxis = list(title = "Papers"))
    })

    output$citation_type <- renderPlotly({
      papers <- filtered_papers()
      if (!nrow(papers)) return(plotly_empty())
      q <- venue_type_data(papers) |> group_by(venue_group) |> summarise(citations = sum(cited_by_count, na.rm = TRUE), .groups = "drop")
      plot_ly(q, x = ~venue_group, y = ~citations, type = "bar", marker = list(color = "#64748b")) |> layout(xaxis = list(title = ""), yaxis = list(title = "Citations"))
    })

    output$code_type <- renderPlotly({
      papers <- filtered_papers()
      ids <- if (nrow(app_data$paper_code_links)) unique(app_data$paper_code_links$work_id) else character()
      if (!nrow(papers)) return(plotly_empty())
      q <- venue_type_data(papers) |> mutate(has_code = work_id %in% ids) |> group_by(venue_group) |> summarise(score = mean(has_code), .groups = "drop")
      plot_ly(q, x = ~venue_group, y = ~score, type = "bar", marker = list(color = "#16a34a")) |> layout(xaxis = list(title = ""), yaxis = list(title = "Code adoption", tickformat = ".0%"))
    })

    venue_metadata <- reactive({
      papers <- filtered_papers()
      if (!nrow(papers)) return(tibble())
      venue_type_data(papers) |> count(venue_group, venue_id, venue_name, venue_type, quality_label, sort = TRUE)
    })

    output$venue_table <- renderDT({
      datatable(venue_metadata(), options = list(pageLength = 15, scrollX = TRUE), rownames = FALSE)
    })

    output$download_venue_metadata <- downloadHandler(
      filename = function() "venue_metadata_review.csv",
      content = function(file) readr::write_csv(venue_metadata(), file)
    )
  })
}
