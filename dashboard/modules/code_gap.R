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

code_gap_server <- function(id, filtered_papers, top_n = reactive(25)) {
  moduleServer(id, function(input, output, session) {
    code_data <- reactive({
      cg <- app_data$code_gap
      papers <- filtered_papers()
      if (!nrow(cg) || !nrow(papers)) return(tibble())
      cg |>
        filter(.data$work_id %in% papers$work_id) |>
        mutate(
          publication_year = as.integer(as_number(.data$publication_year, NA_real_)),
          cited_by_count = as_number(.data$cited_by_count, 0),
          repo_count_per_paper = as_number(.data$repo_count_per_paper, 0),
          total_stars_per_paper = as_number(.data$total_stars_per_paper, 0),
          total_forks_per_paper = as_number(.data$total_forks_per_paper, 0),
          code_score = as_number(.data$code_score, 0),
          has_code = as_flag(.data$has_code),
          topic_group = coalesce(as.character(.data$topic_group), "Unassigned"),
          venue_name = coalesce(as.character(.data$venue_name), "Unknown venue"),
          quality_label = coalesce(as.character(.data$quality_label), "Unknown")
        )
    })

    output$gap_scatter <- renderPlotly({
      df <- code_data()
      if (!nrow(df)) return(plotly_empty())
      df <- df |>
        filter(is.finite(.data$cited_by_count), is.finite(.data$code_score)) |>
        mutate(
          citation_axis = pmax(1, .data$cited_by_count),
          marker_size = pmin(45, pmax(6, 6 + sqrt(pmax(0, .data$total_stars_per_paper))))
        )
      if (!nrow(df)) return(plotly_empty())
      plot_ly(df, x = ~citation_axis, y = ~code_score, color = ~topic_group, symbol = ~quality_label,
        size = ~marker_size,
        sizes = c(6, 34),
        text = ~paste0(title, "<br>Venue: ", venue_name, "<br>Year: ", publication_year, "<br>Citations: ", cited_by_count, "<br>Code score: ", round(code_score, 2)),
        type = "scatter", mode = "markers", marker = list(opacity = 0.72, line = list(width = 0.5, color = "rgba(15,23,42,0.35)"))) |>
        layout(xaxis = list(title = "Citation count", type = "log"), yaxis = list(title = "Code score", rangemode = "tozero"), legend = list(orientation = "h"))
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
      papers <- filtered_papers()
      links <- app_data$paper_code_links
      countries <- app_data$paper_countries
      if (!nrow(papers) || !nrow(links) || !nrow(countries)) {
        return(sankeyNetwork(Links = data.frame(source = integer(), target = integer(), value = numeric()), Nodes = data.frame(name = character()), Source = "source", Target = "target", Value = "value", NodeID = "name"))
      }
      cap <- suppressWarnings(as.integer(top_n()))
      if (is.na(cap) || cap < 5) cap <- 25
      country_lookup <- app_data$country_map |>
        select(any_of(c("country_code", "country_name"))) |>
        distinct()
      flow <- links |>
        mutate(repo_full_name = paste(.data$repo_owner, .data$repo_name, sep = "/")) |>
        inner_join(papers |> select(work_id, topic_group), by = "work_id") |>
        inner_join(countries, by = "work_id") |>
        left_join(country_lookup, by = "country_code", suffix = c("_raw", "_map")) |>
        mutate(
          country_label = coalesce(.data$country_name_map, .data$country_name_raw, .data$country_code),
          topic_group = coalesce(as.character(.data$topic_group), "Unassigned"),
          repo_full_name = str_trunc(.data$repo_full_name, 34)
        ) |>
        filter(nzchar(.data$country_label), nzchar(.data$topic_group), nzchar(.data$repo_full_name))
      if (!nrow(flow)) {
        return(sankeyNetwork(Links = data.frame(source = integer(), target = integer(), value = numeric()), Nodes = data.frame(name = character()), Source = "source", Target = "target", Value = "value", NodeID = "name"))
      }

      top_countries <- flow |> count(country_label, sort = TRUE) |> slice_head(n = min(8, cap)) |> pull(country_label)
      top_topics <- flow |> count(topic_group, sort = TRUE) |> slice_head(n = min(10, cap)) |> pull(topic_group)
      top_repos <- flow |> count(repo_full_name, sort = TRUE) |> slice_head(n = min(18, max(10, cap))) |> pull(repo_full_name)
      flow <- flow |>
        filter(.data$country_label %in% top_countries, .data$topic_group %in% top_topics, .data$repo_full_name %in% top_repos)
      if (!nrow(flow)) {
        return(sankeyNetwork(Links = data.frame(source = integer(), target = integer(), value = numeric()), Nodes = data.frame(name = character()), Source = "source", Target = "target", Value = "value", NodeID = "name"))
      }

      country_topic <- flow |>
        distinct(.data$work_id, .data$country_label, .data$topic_group) |>
        count(.data$country_label, .data$topic_group, name = "value") |>
        transmute(source = paste0("Country: ", .data$country_label), target = paste0("Topic: ", .data$topic_group), value = .data$value)
      topic_repo <- flow |>
        distinct(.data$work_id, .data$topic_group, .data$repo_full_name) |>
        count(.data$topic_group, .data$repo_full_name, name = "value") |>
        transmute(source = paste0("Topic: ", .data$topic_group), target = paste0("Repo: ", .data$repo_full_name), value = .data$value)
      sankey <- bind_rows(country_topic, topic_repo) |>
        group_by(.data$source, .data$target) |>
        summarise(value = sum(.data$value, na.rm = TRUE), .groups = "drop") |>
        arrange(desc(.data$value))
      if (!nrow(sankey)) {
        return(sankeyNetwork(Links = data.frame(source = integer(), target = integer(), value = numeric()), Nodes = data.frame(name = character()), Source = "source", Target = "target", Value = "value", NodeID = "name"))
      }
      labels <- unique(c(sankey$source, sankey$target))
      nodes <- data.frame(name = labels)
      links <- sankey |> mutate(source = match(source, labels) - 1, target = match(target, labels) - 1) |> select(source, target, value)
      sankeyNetwork(Links = links, Nodes = nodes, Source = "source", Target = "target", Value = "value", NodeID = "name", fontSize = 11, nodeWidth = 22, sinksRight = FALSE)
    })

    output$no_code_table <- renderDT({
      df <- code_data()
      if (!nrow(df)) return(empty_dt("No paper records match the active filters."))
      df |> filter(!has_code) |> arrange(desc(cited_by_count)) |> select(title, publication_year, venue_name, quality_label, topic_group, cited_by_count) |> slice_head(n = 50) |>
        datatable(options = list(pageLength = 10, scrollX = TRUE), rownames = FALSE)
    })

    output$code_impact_table <- renderDT({
      df <- code_data()
      if (!nrow(df)) return(empty_dt("No paper records match the active filters."))
      df |> filter(code_score > 0 | total_stars_per_paper > 0) |> arrange(desc(code_score), desc(total_stars_per_paper)) |> select(title, publication_year, venue_name, topic_group, cited_by_count, total_stars_per_paper, total_forks_per_paper, code_score) |> slice_head(n = 50) |>
        datatable(options = list(pageLength = 10, scrollX = TRUE), rownames = FALSE)
    })
  })
}
