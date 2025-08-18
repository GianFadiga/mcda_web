# analyzer_app/analysis_utils.py
"""
Módulo de análise de dados para comparação de produtos.

Este módulo permite carregar, analisar e visualizar dados de comparação de produtos
com base em critérios pré-definidos, gerando pontuações e recomendações.
"""

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
import csv
from typing import Dict, Optional, List, Union, Any


class DataAnalyzer:
    """Classe principal para análise e comparação de dados de produtos."""

    def __init__(self, file_path: str) -> None:
        """Inicializa o analisador com o caminho do arquivo de dados."""
        self.file_path = file_path
        self.df = None
        self.weights = None
        self.data_types = None
        self.proportionality = None
        self.good_values = None
        self.neutral_values = None
        self.calculation_df = None
        self.string_columns_map = {}
        self.model_column = None

    # ===============================================================
    # SEÇÃO DE CARREGAMENTO E PREPARAÇÃO DE DADOS (NOSSA VERSÃO ROBUSTA)
    # ===============================================================

    def load_and_prepare_data(self) -> None:
        """Carrega e prepara os dados para análise."""
        self._load_raw_data()
        self._clean_empty_columns()
        self._extract_configurations()
        self._map_string_columns()
        self._extract_reference_values()
        self._prepare_calculation_data()
        self._convert_data_types()

    def _load_raw_data(self) -> None:
        """Carrega os dados brutos do CSV, com detecção robusta de separador e cabeçalho."""
        try:
            with open(self.file_path, 'r', encoding='UTF-8', newline='') as f:
                first_line = f.readline()
                f.seek(0) 
                
                try:
                    dialect = csv.Sniffer().sniff(f.read(2048))
                    separator = dialect.delimiter
                except csv.Error:
                    separator = ',' 
                
                f.seek(0)
                print(f"Separador '{separator}' detectado.")

                config_keywords = ['PESO', 'TIPO', 'FUNCAO', 'BOM', 'NEUTRO']
                is_data_row = any(first_line.strip().upper().startswith(kw) for kw in config_keywords)

            if not is_data_row:
                self.df = pd.read_csv(self.file_path, sep=separator, skipinitialspace=True)
                print("Arquivo carregado com cabeçalho.")
            else:
                self.df = pd.read_csv(self.file_path, sep=separator, skipinitialspace=True, header=None)
                self.df.columns = [f'Coluna_{i+1}' for i in range(len(self.df.columns))]
                print("Arquivo carregado sem cabeçalho. Nomes de coluna genéricos foram criados.")

            if not self.df.empty:
                 self.model_column = self.df.columns[0]
            else:
                raise ValueError("Arquivo CSV está vazio ou não pôde ser lido corretamente.")

        except Exception as e:
            raise ValueError(f"Erro ao carregar ou processar arquivo: {str(e)}")


    def _clean_empty_columns(self) -> None:
        """Remove colunas totalmente vazias do DataFrame."""
        self.df = self.df.dropna(axis=1, how='all')

    def _extract_configurations(self) -> None:
        """Extrai configurações de forma flexível, suportando o formato novo e o antigo."""
        if len(self.df) < 3:
            raise ValueError("Arquivo CSV não contém linhas suficientes para configurações")

        first_col = self.df.columns[0]
        
        first_val = self.df[first_col].iloc[0]
        is_new_format = isinstance(first_val, str) and first_val.upper() in ['PESO', 'TIPO', 'FUNCAO']

        if is_new_format:
            try:
                print("Tentando extrair configuração pelo método novo (com identificadores).")
                if not all(x in self.df[first_col].values for x in ['PESO', 'TIPO', 'FUNCAO']):
                     raise ValueError("Identificadores de configuração (PESO, TIPO, FUNCAO) não encontrados.")

                self.weights = self.df[self.df[first_col] == 'PESO'].iloc[0].drop(first_col).dropna().astype(float)
                self.data_types = self.df[self.df[first_col] == 'TIPO'].iloc[0].drop(first_col).dropna()
                self.proportionality = self.df[self.df[first_col] == 'FUNCAO'].iloc[0].drop(first_col).dropna()
                return
            except (IndexError, ValueError) as e:
                print(f"Falha no método novo: {e}. Tentando método antigo.")

        print("Extraindo configuração pelo método antigo (baseado em posição).")
        self.df.loc[self.df.index[0], first_col] = 'PESO'
        self.df.loc[self.df.index[1], first_col] = 'TIPO'
        self.df.loc[self.df.index[2], first_col] = 'FUNCAO'
        
        # O formato antigo não tem identificador para BOM/NEUTRO na coluna, então precisamos achar por valor
        bom_row = self.df[self.df.apply(lambda row: 'BOM' in row.values, axis=1)]
        if not bom_row.empty: self.df.loc[bom_row.index[0], first_col] = 'BOM'

        neutro_row = self.df[self.df.apply(lambda row: 'NEUTRO' in row.values, axis=1)]
        if not neutro_row.empty: self.df.loc[neutro_row.index[0], first_col] = 'NEUTRO'


        self.weights = self.df[self.df[first_col] == 'PESO'].iloc[0].drop(first_col).dropna().astype(float)
        self.data_types = self.df[self.df[first_col] == 'TIPO'].iloc[0].drop(first_col).dropna()
        self.proportionality = self.df[self.df[first_col] == 'FUNCAO'].iloc[0].drop(first_col).dropna()


    def _map_string_columns(self) -> None:
        """Mapeia colunas de string para suas colunas de pontos correspondentes."""
        print("\n[DEBUG] Iniciando o mapeamento de colunas de string...")
        self.string_columns_map = {}

        if self.data_types is None:
            print("[DEBUG] Tipos de dados não carregados. Abortando mapeamento.")
            raise ValueError("Tipos de dados não foram carregados corretamente")

        string_cols = [col for col in self.data_types.index if self.data_types[col] == 'string']
        print(f"[DEBUG] Colunas do tipo 'string' encontradas: {string_cols}")

        for col in string_cols:
            try:
                col_idx = list(self.df.columns).index(col)
                if col_idx + 1 < len(self.df.columns):
                    pts_col = self.df.columns[col_idx + 1]
                    new_pts_col_name = f"{col}_points"
                    self.string_columns_map[col] = new_pts_col_name
                    self.df = self.df.rename(columns={pts_col: new_pts_col_name})
                    print(f"[DEBUG] Sucesso: Coluna '{col}' mapeada para '{new_pts_col_name}' (antiga '{pts_col}').")
                else:
                    print(f"[DEBUG] Aviso: Coluna '{col}' é a última, não há coluna de pontos para mapear.")
            except (ValueError, IndexError):
                print(f"[DEBUG] Erro: Não foi possível mapear a coluna de pontos para '{col}'.")

    def _extract_reference_values(self) -> None:
        """Extrai valores de referência BOM e NEUTRO."""
        good_row = self.df[self.df[self.model_column] == 'BOM']
        neutral_row = self.df[self.df[self.model_column] == 'NEUTRO']
        self.good_values = good_row.iloc[0].dropna() if not good_row.empty else pd.Series(dtype='object')
        self.neutral_values = neutral_row.iloc[0].dropna() if not neutral_row.empty else pd.Series(dtype='object')
        if good_row.empty or neutral_row.empty: print("Aviso: Linhas de referência 'BOM' ou 'NEUTRO' não encontradas")

    def _prepare_calculation_data(self) -> None:
        """Prepara o DataFrame para cálculos, removendo linhas de configuração."""
        config_identifiers = ['PESO', 'TIPO', 'FUNCAO', 'BOM', 'NEUTRO']
        self.calculation_df = self.df[~self.df[self.model_column].isin(config_identifiers)].reset_index(drop=True).copy()


    def _convert_data_types(self) -> None:
        """Converte os tipos de dados conforme especificado."""
        for col in self.data_types.index:
            if col not in self.calculation_df.columns: continue
            dtype = self.data_types[col]
            try:
                if dtype == 'number': self._convert_numeric_column(col)
                elif dtype == 'boolean': self._convert_boolean_column(col)
                elif dtype == 'string': self.calculation_df[col] = self.calculation_df[col].astype(str)
            except Exception as e: print(f"Erro ao converter coluna '{col}': {str(e)}")

    def _convert_numeric_column(self, col: str) -> None:
        """Converte coluna numérica e valores de referência."""
        if col in self.good_values: self.good_values[col] = pd.to_numeric(self.good_values.get(col), errors='coerce')
        if col in self.neutral_values: self.neutral_values[col] = pd.to_numeric(self.neutral_values.get(col), errors='coerce')
        self.calculation_df[col] = pd.to_numeric(self.calculation_df[col], errors='coerce')

    def _convert_boolean_column(self, col: str) -> None:
        """Converte coluna booleana e valores de referência."""
        if col in self.good_values: self.good_values[col] = str(self.good_values.get(col, '')).strip().upper() == 'TRUE'
        if col in self.neutral_values: self.neutral_values[col] = str(self.neutral_values.get(col, '')).strip().upper() == 'TRUE'
        self.calculation_df[col] = self.calculation_df[col].astype(str).str.strip().str.upper().map({'TRUE': True, 'FALSE': False}).fillna(False).astype(bool)

    # ... (Restante das funções de cálculo de score) ...
    def calculate_scores(self) -> None:
        self._validate_calculation_preconditions()
        for col in self.weights.index: self._process_column_for_scoring(col)
        self._calculate_total_score()

    def _validate_calculation_preconditions(self) -> None:
        if self.calculation_df is None or self.data_types is None or self.weights is None:
            raise ValueError("Dados não carregados. Execute load_and_prepare_data() primeiro")

    def _process_column_for_scoring(self, col: str) -> None:
        score_col_name = f"{col}_score"
        dtype = self.data_types.get(col)
        if dtype in ['number', 'boolean']: self._calculate_numeric_score(col, score_col_name)
        elif dtype == 'string': self._calculate_string_score(col, score_col_name)

    def _calculate_numeric_score(self, col: str, score_col_name: str) -> None:
        good_value = self.good_values.get(col)
        neutral_value = self.neutral_values.get(col)
        weight = self.weights.get(col, 0)
        proportionality = self.proportionality.get(col)
        if pd.isna(good_value) or pd.isna(neutral_value) or not proportionality:
            self.calculation_df[score_col_name] = 0; return
        self.calculation_df[score_col_name] = self.calculation_df.apply(
            lambda row: self._calculate_numeric_score_value(row.get(col), good_value, neutral_value, weight, proportionality), axis=1)

    def _calculate_string_score(self, col: str, score_col_name: str) -> None:
        if col not in self.calculation_df.columns: self.calculation_df[score_col_name] = 0; return
        self.calculation_df[score_col_name] = self.calculation_df.apply(lambda row: self._calculate_string_score_value(row.get(col), col), axis=1)

    def _calculate_total_score(self) -> None:
        score_columns = [c for c in self.calculation_df.columns if c.endswith('_score')]
        self.calculation_df['Total_Score'] = self.calculation_df[score_columns].sum(axis=1) if score_columns else 0

    def _calculate_numeric_score_value(self, value: Any, good_value: Any, neutral_value: Any, weight: float, prop_type: str) -> float:
        if pd.isna(value): return 0
        if isinstance(value, (bool, np.bool_)): return self._calculate_boolean_score(value, good_value, neutral_value, weight)
        if pd.isna(good_value) or pd.isna(neutral_value) or good_value == neutral_value: return 0
        if prop_type == 'proportional': return self._calculate_proportional_score(value, good_value, neutral_value, weight)
        if prop_type == 'i_proportional': return self._calculate_inverse_proportional_score(value, good_value, neutral_value, weight)
        return 0

    def _calculate_boolean_score(self, value: bool, good_value: bool, neutral_value: bool, weight: float) -> float:
        if good_value == neutral_value: return weight if value == good_value else 0
        if value == good_value: return weight
        if value == neutral_value: return 0
        return -weight

    def _calculate_proportional_score(self, value: float, good: float, neutral: float, weight: float) -> float:
        # Caso onde bom == neutro, qualquer valor diferente é 0
        if good == neutral:
            return weight if value == good else 0
        
        # Caso crescente normal (ex: Potência - 120cv é melhor que 90cv)
        if good > neutral:
            if value >= good: return weight
            if value >= neutral: return ((value - neutral) / (good - neutral)) * weight
            # Se o valor for pior que o neutro, a penalidade é proporcional à distância
            denominator = neutral if neutral != 0 else 1
            return -((abs(neutral - value)) / abs(denominator)) * weight
        # Caso decrescente (incomum para 'proportional', mas coberto)
        else: # good < neutral
            if value <= good: return weight
            if value <= neutral: return ((neutral - value) / (neutral - good)) * weight
            denominator = neutral if neutral != 0 else 1
            return -((abs(value - neutral)) / abs(denominator)) * weight

    def _calculate_inverse_proportional_score(self, value: float, good: float, neutral: float, weight: float) -> float:
         # Caso onde bom == neutro
        if good == neutral:
            return weight if value == good else 0
            
        # Caso decrescente normal (ex: Preço - 60k é melhor que 85k)
        if good < neutral:
            if value <= good: return weight
            if value <= neutral: return ((neutral - value) / (neutral - good)) * weight
            # Se o valor for pior que o neutro, a penalidade é proporcional
            denominator = neutral if neutral != 0 else 1
            return -((abs(value - neutral)) / abs(denominator)) * weight
        # Caso crescente (incomum para 'i_proportional', mas coberto)
        else: # good > neutral
            if value >= good: return weight
            if value >= neutral: return ((value - good) / (neutral - good)) * weight
            denominator = neutral if neutral != 0 else 1
            return -((abs(neutral - value)) / abs(denominator)) * weight
    
    def _calculate_string_score_value(self, value: str, column: str) -> float:
        """Calcula pontuação para um valor de string individual."""
        print(f"\n[DEBUG] Calculando score para string. Coluna: '{column}', Valor: '{value}'")
        points_column = self.string_columns_map.get(column)

        if not points_column or points_column not in self.df.columns:
            print(f"[DEBUG] Erro: Coluna de pontos '{points_column}' não encontrada no DataFrame.")
            return 0

        try:
            # Usando a lógica de filtro robusta em vez de iloc[5:]
            config_identifiers = ['PESO', 'TIPO', 'FUNCAO', 'BOM', 'NEUTRO']
            mapping_data = self.df[~self.df[self.model_column].isin(config_identifiers)].copy()
            
            mapping_data[points_column] = pd.to_numeric(mapping_data[points_column], errors='coerce')
            mapping_data = mapping_data.dropna(subset=[column, points_column])

            mapping = dict(zip(mapping_data[column], mapping_data[points_column]))
            
            if not mapping:
                print("[DEBUG] Erro: O dicionário de mapeamento (cor -> pontos) está vazio.")
                return 0
            
            print(f"[DEBUG] Dicionário de mapeamento criado: {mapping}")

            clean_value = str(value).strip()
            base_score = mapping.get(clean_value, 0)
            print(f"[DEBUG] Pontuação base para '{clean_value}': {base_score}")
            
            column_weight = float(self.weights.get(column, 0))
            print(f"[DEBUG] Peso para a coluna '{column}': {column_weight}")

            final_score = base_score * column_weight
            print(f"[DEBUG] Pontuação final (base * peso): {final_score}")
            
            return final_score
        except Exception as e:
            print(f"[DEBUG] Exceção inesperada ao calcular score de string: {str(e)}")
            return 0

    # ===============================================================
    # SEUS MÉTODOS ORIGINAIS DE GERAÇÃO DE GRÁFICOS
    # ===============================================================

    def generate_visualizations(self) -> Dict[str, str]:
        """Gera todas as visualizações de análise e retorna como dicionário de HTML."""
        visualizations = {}
        if self.calculation_df is None:
            print("Dados não disponíveis para geração de gráficos")
            return visualizations
        try:
            visualizations['total_score'] = self._generate_total_score_chart()
            numeric_charts = self._generate_numeric_charts()
            if numeric_charts: visualizations.update(numeric_charts)
            string_charts = self._generate_string_charts()
            if string_charts: visualizations.update(string_charts)
            boolean_charts = self._generate_boolean_charts()
            if boolean_charts: visualizations.update(boolean_charts)
        except Exception as e:
            print(f"Erro ao gerar visualizações: {str(e)}")
        return visualizations

    def _generate_total_score_chart(self) -> str:
        """Gera gráfico de barras para pontuação total e retorna como HTML."""
        if 'Total_Score' not in self.calculation_df.columns:
            return "<div>Pontuação total não disponível</div>"
        max_theoretical_score = self.weights.sum() if self.weights is not None else 1.0
        analysis_df = self.calculation_df[~self.calculation_df[self.model_column].isin(['BOM', 'NEUTRO'])].copy()
        analysis_df.dropna(subset=['Total_Score'], inplace=True)
        if analysis_df.empty: return "<div>Nenhum dado válido para pontuação total</div>"
        analysis_df = analysis_df.sort_values('Total_Score', ascending=False)
        analysis_df['Color_Category'] = analysis_df['Total_Score'].apply(lambda x: 'Positiva' if x >= 0 else 'Negativa')
        fig = px.bar(
            analysis_df, x='Total_Score', y=self.model_column, orientation='h',
            color='Color_Category', color_discrete_map={'Positiva': 'lightgreen', 'Negativa': 'palevioletred'},
            hover_name=self.model_column, hover_data={'Total_Score': ':.2f'}, title='Pontuação Total dos Modelos'
        )
        fig.update_layout(
            yaxis={'categoryorder': 'total ascending'}, plot_bgcolor='white', paper_bgcolor='white',
            legend_title_text='Resultado', xaxis_title='Pontuação Total', yaxis_title='Modelo'
        )
        fig.add_vline(x=0, line_dash='dash', line_color='black')
        fig.add_vline(x=max_theoretical_score, line_dash='dash', line_color='black')
        self._add_reference_annotation(fig, max_theoretical_score, len(analysis_df), "Desejável (BOM)<br>(NEUTRO)")
        self._add_reference_annotation(fig, 0, len(analysis_df), "Mínimo Aceitável<br>(NEUTRO)")
        if not analysis_df.empty:
            best_product = analysis_df.iloc[0]
            fig.add_annotation(
                x=best_product['Total_Score'], y=best_product[self.model_column], text="🏆 Melhor Produto",
                showarrow=False, font=dict(color="#00008B", size=12), bgcolor="white",
                bordercolor="black", borderwidth=1, borderpad=4, xshift=-15, yshift=25
            )
        return fig.to_html(full_html=False, include_plotlyjs='cdn')

    def _add_reference_annotation(self, fig: go.Figure, x_value: float, y_position: int, text: str) -> None:
        """Adiciona anotação de referência ao gráfico."""
        fig.add_annotation(
            x=x_value, y=y_position - 1, xref="x", yref="y", text=text, showarrow=True,
            font=dict(size=16, color="#000000"), arrowhead=2, arrowsize=1, arrowwidth=2,
            arrowcolor="#636363", ax=0, ay=-45, bordercolor="#c7c7c7", borderwidth=2,
            borderpad=4, bgcolor='white', opacity=1
        )

    def _generate_numeric_charts(self) -> Dict[str, str]:
        """Gera gráficos para colunas numéricas e retorna como dicionário de HTML."""
        charts = {}
        if self.data_types is None: return charts
        numeric_cols = [col for col in self.data_types.index if self.data_types[col] == 'number' and col in self.calculation_df.columns]
        for col in numeric_cols:
            df = self.calculation_df[~self.calculation_df[self.model_column].isin(['BOM', 'NEUTRO'])][[self.model_column, col]].copy()
            df.dropna(subset=[col], inplace=True)
            if df.empty: continue
            good_value = self.good_values.get(col)
            neutral_value = self.neutral_values.get(col)
            is_inverse = self.proportionality.get(col, '').lower() == 'i_proportional'
            df['Color_Category'] = df.apply(lambda x: self._classify_numeric_value(x[col], good_value, neutral_value, is_inverse), axis=1)
            df = df.sort_values(col, ascending=not is_inverse)
            fig = px.bar(
                df, x=col, y=self.model_column, orientation='h', color='Color_Category',
                color_discrete_map={'Positiva': 'lightgreen', 'Negativa': 'palevioletred', 'Neutra': 'lightgray'},
                hover_name=self.model_column, hover_data={col: ':.2f'}, title=f"{col} {'(Inversamente Proporcional)' if is_inverse else ''}"
            )
            fig.update_layout(plot_bgcolor='white', paper_bgcolor='white', legend_title_text='Resultado', xaxis_title=col, yaxis_title='Modelo')
            if pd.notna(neutral_value): self._add_reference_line(fig, float(neutral_value), len(df), "Mínimo Aceitável<br>(NEUTRO)", is_inverse)
            if pd.notna(good_value): self._add_reference_line(fig, float(good_value), len(df), "Desejável (BOM)", is_inverse)
            charts[f'numeric_{col}'] = fig.to_html(full_html=False, include_plotlyjs='cdn')
        return charts

    def _classify_numeric_value(self, value: float, good_value: float, neutral_value: float, is_inverse: bool) -> str:
        """Classifica um valor numérico como Positivo, Negativo ou Neutro."""
        if pd.isna(neutral_value) or pd.isna(value): return 'Neutra'
        value, neutral_value = float(value), float(neutral_value)
        if is_inverse: return 'Positiva' if value <= neutral_value else 'Negativa'
        return 'Positiva' if value >= neutral_value else 'Negativa'

    def _add_reference_line(self, fig: go.Figure, value: float, y_position: int, text: str, is_inverse: bool) -> None:
        """Adiciona linha de referência ao gráfico numérico."""
        fig.add_vline(x=value, line_dash='dash', line_color='black')
        fig.add_annotation(
            x=value, y=y_position - 1, text=text, showarrow=True, font=dict(size=16, color="#000000"),
            arrowhead=2, arrowsize=1, arrowwidth=2, arrowcolor="#636363", ax=0, ay=-45,
            bordercolor="#c7c7c7", borderwidth=2, borderpad=4, bgcolor='white', opacity=1
        )

    def _generate_string_charts(self) -> Dict[str, str]:
        """Gera gráficos para colunas de string e retorna como dicionário de HTML."""
        charts = {}
        if self.data_types is None: return charts
        string_cols = [col for col in self.data_types.index if self.data_types.get(col) == 'string' and col in self.calculation_df.columns]
        for col in string_cols:
            pts_col = self.string_columns_map.get(col)
            if not pts_col or pts_col not in self.df.columns: continue
            try:
                mapping_data = self.df.iloc[5:].copy()
                mapping_data[pts_col] = pd.to_numeric(mapping_data[pts_col], errors='coerce')
                mapping_data.dropna(subset=[col, pts_col], inplace=True)
                string_mapping = dict(zip(mapping_data[col], mapping_data[pts_col]))
                if not string_mapping: continue
                df_plot = self.calculation_df[~self.calculation_df[self.model_column].isin(['BOM', 'NEUTRO'])][[self.model_column, col]].copy()
                df_plot['BaseValue'] = df_plot[col].map(string_mapping).fillna(0)
                df_plot = df_plot.sort_values('BaseValue', ascending=False)
                df_plot['Position'] = range(len(df_plot))
                fig = px.scatter(
                    df_plot, x='Position', y='BaseValue', color=col, hover_name=self.model_column,
                    title=f'Comparação de {col.capitalize()} entre Modelos (Pontuação Base)', size_max=15,
                    hover_data={'Position': False, 'BaseValue': True, col: True},
                    labels={'BaseValue': 'Pontuação Base (do CSV)', col: col.capitalize()}
                )
                good_str, neutral_str = self.good_values.get(col), self.neutral_values.get(col)
                good_base, neutral_base = string_mapping.get(good_str), string_mapping.get(neutral_str)
                if good_base is not None: fig.add_hline(y=good_base, line_dash='dash', line_color='green', annotation_text=f"BOM: '{good_str}' ({good_base:.2f})", annotation_position="top right", annotation_font=dict(color='green', size=12))
                if neutral_base is not None: fig.add_hline(y=neutral_base, line_dash='dash', line_color='orange', annotation_text=f"NEUTRO: '{neutral_str}' ({neutral_base:.2f})", annotation_position="bottom right", annotation_font=dict(color='orange', size=12))
                fig.update_layout(
                    xaxis=dict(title='Modelos Ordenados por Pontuação Base', showticklabels=False, showgrid=False, zeroline=False),
                    yaxis=dict(title='Pontuação Base (Definida no CSV)', showgrid=True, gridcolor='lightgray', zeroline=True, zerolinecolor='lightgray'),
                    plot_bgcolor='white', paper_bgcolor='white', margin=dict(l=40, r=40, t=60, b=40),
                    legend=dict(title_text=col.capitalize(), orientation='h', yanchor='bottom', y=-0.3, xanchor='center', x=0.5),
                    hoverlabel=dict(bgcolor='white', font_size=12, font_family='Arial')
                )
                fig.update_traces(marker=dict(size=12, line=dict(width=1, color='DarkSlateGrey'), opacity=0.8))
                charts[f'string_{col}'] = fig.to_html(full_html=False, include_plotlyjs='cdn')
            except Exception as e: print(f"Erro ao gerar gráfico para '{col}': {str(e)}")
        return charts

    def _generate_boolean_charts(self) -> Dict[str, str]:
        """Gera gráficos para colunas booleanas e retorna como dicionário de HTML."""
        charts = {}
        if self.data_types is None: return charts
        bool_cols = [col for col in self.data_types.index if self.data_types[col] == 'boolean' and col in self.calculation_df.columns]
        for col in bool_cols:
            df = self.calculation_df[~self.calculation_df[self.model_column].isin(['BOM', 'NEUTRO'])][[self.model_column, col]].copy()
            df['Value'] = df[col].map({True: 1, False: 0})
            df['Size'] = 20
            fig = px.scatter(
                df, x=self.model_column, y='Value', color=col, color_discrete_map={True: '#4CAF50', False: '#F44336'},
                size='Size', title=f'{col} por Modelo', hover_name=self.model_column,
                hover_data={'Value': False, 'Size': False}, category_orders={col: [True, False]}
            )
            fig.for_each_trace(lambda t: t.update(name='SIM' if t.name == 'True' else 'NÃO'))
            fig.update_yaxes(range=[-0.5, 1.5], tickvals=[0, 1], ticktext=['Não', 'Sim'], showgrid=False)
            fig.add_hline(y=1, line_dash='dash', line_color='green')
            fig.add_hline(y=0, line_dash='dash', line_color='orange')
            fig.update_layout(xaxis_title=None, yaxis_title=None, plot_bgcolor='white', paper_bgcolor='white')
            charts[f'boolean_{col}'] = fig.to_html(full_html=False, include_plotlyjs='cdn')
        return charts

    # ===============================================================
    # NOVAS FUNÇÕES DO PÓDIO
    # ===============================================================

    def get_podium_details(self) -> list:
        """Retorna uma lista com os detalhes dos 3 melhores produtos para o pódio."""
        if 'Total_Score' not in self.calculation_df.columns: return []
        sorted_df = self.calculation_df.sort_values('Total_Score', ascending=False)
        top_products = sorted_df.head(3)
        podium_list = []
        for rank, (index, product) in enumerate(top_products.iterrows(), 1):
            details_list = self._get_recommendation_details(product)
            podium_list.append({
                'rank': rank, 'name': product[self.model_column], 'score': f"{product['Total_Score']:.2f}",
                'details': details_list
            })
        return podium_list

    def _get_recommendation_details(self, product: pd.Series) -> list:
        """Retorna uma lista de strings com a justificativa da pontuação de um produto."""
        if self.weights is None: return []
        details_list = []
        sorted_criteria = self.weights.sort_values(ascending=False).index
        for col in sorted_criteria:
            score_col = f"{col}_score"
            if score_col not in product or pd.isna(product[score_col]): continue
            score = product[score_col]
            current_value = product.get(col, "N/A")
            if isinstance(current_value, bool): value_str = "Sim" if current_value else "Não"
            elif isinstance(current_value, (int, float)): value_str = f"{current_value:.1f}"
            else: value_str = str(current_value)
            justification = "[Vantagem]" if score > 0 else "[Desvantagem]" if score < 0 else "[Neutro]"
            details_list.append(f"<b>{col}:</b> {value_str} {justification} (Pontos: {score:.2f})")
        return details_list