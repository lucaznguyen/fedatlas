code_gap_ui <- function(id) {
  ns <- NS(id)
  div(class = "section-grid",
    card("Citation Impact vs Code Impact", withSpinner(plotlyOutput(ns("gap_scatter"), height = "460px")), caption("Papers in the upper-left are code-influential with lower citation impact; lower-right papers are highly cited with little or no code signal."), class = "span-8"),
    card("Research-to-Code by Topic", withSpinner(plotlyOutput(ns("rtc_topic"), height = "460px")), class = "span-4"),
    card("Research-to-Code by Country", withSpinner(plotlyOutput(ns("rtc_country"), height = "330px")), class = "span-4"),
    card("Research-to-Code by Venue", withSpinner(plotlyOutput(ns("rtc_venue"), height = "330px")), class = "span-4"),
    card("Research-to-Code by Year", withSpinner(plotlyOutput(ns("rtc_year"), height = "330px")), class = "span-4"),
    card("Country to Topic to Repository Flow", withSpinner(sankeyNetworkOutput(ns("sankey"), height = "360px")), class = "span-12"),
    card("Highly Cited Papers Without Code", withSpinner(DTOutput(ns("no_code_table"))), class = "span-6"),
    card("High Code Impact Papers", withSpinner(DTOutput(ns("code_impact_table"))), class = "span-6")
  )
}

code_gap_server <- function(id, filtered_papers) {
  moduleServer(id, function(input, output, session) {
    code_data <- reactive({
      cg <- app_data$code_gap
      papers <- filtered_papers()
      if (!nrow(cg) || !nrow(papers)) return(tibble())
      cg |> filter(work_id %in% papers$work_id)
    })

    output$gap_scatter <- renderPlotly({
      df <- code_data()
      if (!nrow(df)) return(plotly_empty())
      plot_ly(df, x = ~pmax(1, coalesce(cited_by_count, 0)), y = ~code_score, color = ~topic_group, symbol = ~quality_label,
        size = ~pmax(1, coalesce(total_stars_per_paper, 0)),
        text = ~paste0(title, "<br>Venue: ", venue_name, "<br>Year: ", publication_year, "<br>Citations: ", cited_by_count, "<br>Code score: ", round(code_score, 2)),
        type = "scatter", mode = "markers", marker = list(opacity = 0.78)) |>
        layout(xaxis = list(title = "Citation count", type = "log"), yaxis = list(title = "Code score"))
    })

    output$rtc_topic <- renderPlotly({
      rtc <- app_data$research_to_code
      if (!nrow(rtc)) return(plotly_empty())
      top <- rtc |> filter(group_type == "topic") |> group_by(group_value) |> summarise(score = mean(research_to_code_score, na.rm = TRUE), papers = sum(total_papers, na.rm = TRUE), .groups = "drop") |> arrange(desc(score)) |> slice_head(n = 15)
      plot_ly(top, x = ~score, y = ~reorder(group_value, score), type = "bar", orientation = "h", marker = list(color = "#16a34a")) |>
        layout(xaxis = list(title = "Research-to-Code Score", tickformat = ".0%"), yaxis = list(title = ""))
    })

    rtc_bar <- function(group_type, color) {
      rtc <- app_data$research_to_code
      if (!nrow(rtc)) return(plotly_empty())
      top <- rtc |> filter(.data$group_type == !!group_type) |> group_by(group_value) |> summarise(score = mean(research_to_code_score, na.rm = TRUE), papers = sum(total_papers, na.rm = TRUE), .groups = "drop") |> arrange(desc(score)) |> slice_head(n = 10)
      plot_ly(top, x = ~score, y = ~reorder(group_value, score), type = "bar", orientation = "h", marker = list(color = color)) |>
        layout(xaxis = list(title = "Score", tickformat = ".0%"), yaxis = list(title = ""))
    }

    output$rtc_country <- renderPlotly(rtc_bar("country", "#38bdf8"))
    output$rtc_venue <- renderPlotly(rtc_bar("venue", "#64748b"))
    output$rtc_year <- renderPlotly({
      rtc <- app_data$research_to_code
      if (!nrow(rtc)) return(plotly_empty())
      yr <- rtc |> filter(group_type == "year") |> mutate(year = as.numeric(group_value)) |> arrange(year)
      plot_ly(yr, x = ~year, y = ~research_to_code_score, type = "scatter", mode = "lines+markers", line = list(color = "#2563eb")) |>
        layout(xaxis = list(title = ""), yaxis = list(title = "Score", tickformat = ".0%"))
    })

    output$sankey <- renderSankeyNetwork({
      sankey <- read_csv_safe("dashboard_sankey.csv")
      if (!nrow(sankey)) {
        return(sankeyNetwork(Links = data.frame(source = integer(), target = integer(), value = numeric()), Nodes = data.frame(name = character()), Source = "source", Target = "target", Value = "value", NodeID = "name"))
      }
      labels <- unique(c(sankey$source, sankey$target))
      nodes <- data.frame(name = labels)
      links <- sankey |> mutate(source = match(source, labels) - 1, target = match(target, labels) - 1) |> select(source, target, value)
      sankeyNetwork(Links = links, Nodes = nodes, Source = "source", Target = "target", Value = "value", NodeID = "name", fontSize = 12, nodeWidth = 18)
    })

    output$no_code_table <- renderDT({
      df <- code_data()
      if (!nrow(df)) return(datatable(tibble()))
      df |> filter(!has_code) |> arrange(desc(cited_by_count)) |> select(title, publication_year, venue_name, quality_label, topic_group, cited_by_count) |> slice_head(n = 50) |>
        datatable(options = list(pageLength = 10, scrollX = TRUE), rownames = FALSE)
    })

    output$code_impact_table <- renderDT({
      df <- code_data()
      if (!nrow(df)) return(datatable(tibble()))
      df |> arrange(desc(code_score)) |> select(title, publication_year, venue_name, topic_group, cited_by_count, total_stars_per_paper, total_forks_per_paper, code_score) |> slice_head(n = 50) |>
        datatable(options = list(pageLength = 10, scrollX = TRUE), rownames = FALSE)
    })
  })
}
