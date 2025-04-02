"""
Módulo de análise de dados para comparação de produtos.

Este módulo permite carregar, analisar e visualizar dados de comparação de produtos
com base em critérios pré-definidos, gerando pontuações e recomendações.
"""

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
from typing import Dict, Optional, List, Union, Any


class DataAnalyzer:
    """Classe principal para análise e comparação de dados de produtos."""

    def __init__(self, file_path: str) -> None:
        """Inicializa o analisador com o caminho do arquivo de dados.

        Args:
            file_path: Caminho para o arquivo CSV contendo os dados
        """
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
        """Carrega os dados brutos do arquivo CSV."""
        try:
            self.df = pd.read_csv(
                self.file_path,
                encoding='UTF-8',
                sep=',',
                skipinitialspace=True
            )
            self.model_column = self.df.columns[0]
        except Exception as e:
            raise ValueError(f"Erro ao carregar arquivo: {str(e)}")

    def _clean_empty_columns(self) -> None:
        """Remove colunas totalmente vazias do DataFrame."""
        self.df = self.df.dropna(axis=1, how='all')

    def _extract_configurations(self) -> None:
        """Extrai configurações de pesos, tipos de dados e proporcionalidade."""
        if len(self.df) < 3:
            raise ValueError("Arquivo CSV não contém linhas suficientes para configurações")

        self.weights = self.df.iloc[0].dropna().astype(float)
        self.data_types = self.df.iloc[1].dropna()
        self.proportionality = self.df.iloc[2].dropna()

    def _map_string_columns(self) -> None:
        """Mapeia colunas de string para suas colunas de pontos correspondentes."""
        self.string_columns_map = {}

        if self.data_types is None:
            raise ValueError("Tipos de dados não foram carregados corretamente")

        string_cols = [
            col for col in self.data_types.index
            if self.data_types[col] == 'string'
        ]

        for col in string_cols:
            try:
                col_idx = list(self.df.columns).index(col)
                if col_idx + 1 < len(self.df.columns):
                    pts_col = self.df.columns[col_idx + 1]
                    new_pts_col_name = f"{col}_points"
                    self.string_columns_map[col] = new_pts_col_name
                    self.df = self.df.rename(columns={pts_col: new_pts_col_name})
            except (ValueError, IndexError):
                print(f"Aviso: Não foi possível mapear coluna string '{col}'")

    def _extract_reference_values(self) -> None:
        """Extrai valores de referência BOM e NEUTRO."""
        good_row = self.df[self.df[self.model_column] == 'BOM']
        neutral_row = self.df[self.df[self.model_column] == 'NEUTRO']

        self.good_values = good_row.iloc[0].dropna() if not good_row.empty else pd.Series(dtype='object')
        self.neutral_values = neutral_row.iloc[0].dropna() if not neutral_row.empty else pd.Series(dtype='object')

        if good_row.empty or neutral_row.empty:
            print("Aviso: Linhas de referência 'BOM' ou 'NEUTRO' não encontradas")

    def _prepare_calculation_data(self) -> None:
        """Prepara o DataFrame para cálculos, removendo linhas de configuração."""
        self.calculation_df = self.df.iloc[5:].reset_index(drop=True)

    def _convert_data_types(self) -> None:
        """Converte os tipos de dados conforme especificado."""
        for col in self.data_types.index:
            if col not in self.calculation_df.columns:
                continue

            dtype = self.data_types[col]

            try:
                if dtype == 'number':
                    self._convert_numeric_column(col)
                elif dtype == 'boolean':
                    self._convert_boolean_column(col)
                elif dtype == 'string':
                    self.calculation_df[col] = self.calculation_df[col].astype(str)
                elif dtype == 'pts_string':
                    continue
                else:
                    print(f"Aviso: Tipo de dado desconhecido '{dtype}' para coluna '{col}'")
            except Exception as e:
                print(f"Erro ao converter coluna '{col}': {str(e)}")

    def _convert_numeric_column(self, col: str) -> None:
        """Converte coluna numérica e valores de referência."""
        self.good_values[col] = pd.to_numeric(self.good_values.get(col), errors='coerce')
        self.neutral_values[col] = pd.to_numeric(self.neutral_values.get(col), errors='coerce')
        self.calculation_df[col] = pd.to_numeric(self.calculation_df[col], errors='coerce')

    def _convert_boolean_column(self, col: str) -> None:
        """Converte coluna booleana e valores de referência."""
        self.good_values[col] = str(self.good_values.get(col, '')).strip().upper() == 'TRUE'
        self.neutral_values[col] = str(self.neutral_values.get(col, '')).strip().upper() == 'TRUE'
        self.calculation_df[col] = (
            self.calculation_df[col]
            .astype(str)
            .str.strip()
            .str.upper()
            .map({'TRUE': True, 'FALSE': False})
            .fillna(False)
            .astype(bool)
        )

    def calculate_scores(self) -> None:
        """Calcula pontuações para todos os critérios."""
        self._validate_calculation_preconditions()

        print("Colunas disponíveis para cálculo:", list(self.calculation_df.columns))
        print("Pesos aplicáveis:", self.weights.to_dict())
        print("Tipos de Dados:", self.data_types.to_dict())

        for col in self.weights.index:
            self._process_column_for_scoring(col)

        self._calculate_total_score()

    def _validate_calculation_preconditions(self) -> None:
        """Verifica se os dados estão prontos para cálculo."""
        if self.calculation_df is None or self.data_types is None or self.weights is None:
            raise ValueError("Dados não carregados corretamente. Execute load_and_prepare_data() primeiro")

    def _process_column_for_scoring(self, col: str) -> None:
        """Processa uma coluna individual para cálculo de pontuação."""
        print(f"\nProcessando coluna: {col}")

        score_col_name = f"{col}_score"
        dtype = self.data_types.get(col)

        try:
            if dtype in ['number', 'boolean']:
                self._calculate_numeric_score(col, score_col_name)
            elif dtype == 'string':
                self._calculate_string_score(col, score_col_name)

            self._show_partial_results(col, score_col_name)
        except Exception as e:
            print(f"Erro ao processar coluna '{col}': {str(e)}")
            self.calculation_df[score_col_name] = 0

    def _calculate_numeric_score(self, col: str, score_col_name: str) -> None:
        """Calcula pontuação para coluna numérica ou booleana."""
        good_value = self.good_values.get(col)
        neutral_value = self.neutral_values.get(col)
        weight = self.weights.get(col, 0)
        proportionality = self.proportionality.get(col)

        if pd.isna(good_value) or pd.isna(neutral_value) or not proportionality:
            print(f"Aviso: Valores de referência ausentes para '{col}'. Pontuação zerada.")
            self.calculation_df[score_col_name] = 0
            return

        print(f"  Tipo: {self.data_types[col]}, Proporcionalidade: {proportionality}")
        print(f"  Valores BOM: {good_value}, NEUTRO: {neutral_value}, Peso: {weight}")

        self.calculation_df[score_col_name] = self.calculation_df.apply(
            lambda row: self._calculate_numeric_score_value(
                row[col], good_value, neutral_value, weight, proportionality
            ) if col in row else 0,
            axis=1
        )

    def _calculate_string_score(self, col: str, score_col_name: str) -> None:
        """Calcula pontuação para coluna de string."""
        if col not in self.calculation_df.columns:
            print(f"Erro: Coluna string '{col}' não encontrada")
            self.calculation_df[score_col_name] = 0
            return

        pts_col = self.string_columns_map.get(col)
        print(f"  Tipo: string. Coluna de pontos esperada: {pts_col}. Peso: {self.weights.get(col, 0)}")

        self.calculation_df[score_col_name] = self.calculation_df.apply(
            lambda row: self._calculate_string_score_value(row[col], col),
            axis=1
        )

    def _show_partial_results(self, col: str, score_col_name: str) -> None:
        """Mostra resultados parciais para uma coluna."""
        if score_col_name in self.calculation_df:
            print(f"  Resultado parcial (Top 5):\n{self.calculation_df[[col, score_col_name]].head().to_string(index=False)}")
        else:
            print(f"  Aviso: Coluna de pontuação '{score_col_name}' não foi criada.")

    def _calculate_total_score(self) -> None:
        """Calcula a pontuação total somando todas as pontuações individuais."""
        score_columns = [c for c in self.calculation_df.columns if c.endswith('_score')]

        if not score_columns:
            print("\nNenhuma coluna de pontuação gerada. Pontuação total não calculada.")
            self.calculation_df['Total_Score'] = 0
        else:
            print(f"\nColunas usadas para Pontuação Total: {score_columns}")
            self.calculation_df['Total_Score'] = self.calculation_df[score_columns].sum(axis=1)

        print("\nResumo final das pontuações:")
        cols_to_show = [self.model_column] + score_columns + ['Total_Score']
        valid_cols = [c for c in cols_to_show if c in self.calculation_df.columns]
        print(self.calculation_df[valid_cols].head().to_string(index=False))

    def _calculate_numeric_score_value(
        self,
        value: Union[float, bool],
        good_value: Union[float, bool],
        neutral_value: Union[float, bool],
        weight: float,
        proportionality_type: str
    ) -> float:
        """Calcula a pontuação para um valor numérico ou booleano individual."""
        # Tratamento para valores booleanos
        if isinstance(value, (bool, np.bool_)):
            return self._calculate_boolean_score(value, good_value, neutral_value, weight)

        # Verificação de valores inválidos
        if pd.isna(value) or pd.isna(good_value) or pd.isna(neutral_value) or pd.isna(weight):
            return 0

        # Caso onde bom == neutro
        if good_value == neutral_value:
            return 0

        # Lógica de cálculo proporcional
        if proportionality_type == 'proportional':
            return self._calculate_proportional_score(value, good_value, neutral_value, weight)
        elif proportionality_type == 'i_proportional':
            return self._calculate_inverse_proportional_score(value, good_value, neutral_value, weight)

        return 0

    def _calculate_boolean_score(
        self,
        value: bool,
        good_value: bool,
        neutral_value: bool,
        weight: float
    ) -> float:
        """Calcula pontuação para valores booleanos."""
        if good_value == neutral_value:
            return weight if value == good_value else 0
        else:
            if value == good_value:
                return weight
            elif value == neutral_value:
                return 0
            else:
                return -weight

    def _calculate_proportional_score(
        self,
        value: float,
        good_value: float,
        neutral_value: float,
        weight: float
    ) -> float:
        """Calcula pontuação proporcional."""
        if good_value > neutral_value:  # Caso crescente
            if value >= good_value:
                return weight
            elif value >= neutral_value:
                return ((value - neutral_value) / (good_value - neutral_value)) * weight
            else:
                denominator = neutral_value if neutral_value != 0 else 1
                return -((abs(neutral_value - value)) / abs(denominator)) * weight
        elif good_value < neutral_value:  # Caso decrescente
            if value <= good_value:
                return weight
            elif value <= neutral_value:
                return ((value - good_value) / (neutral_value - good_value)) * weight
            else:
                denominator = neutral_value if neutral_value != 0 else 1
                return -((abs(value - neutral_value)) / abs(denominator)) * weight
        else:
            return 0

    def _calculate_inverse_proportional_score(
        self,
        value: float,
        good_value: float,
        neutral_value: float,
        weight: float
    ) -> float:
        """Calcula pontuação inversamente proporcional."""
        if good_value < neutral_value:  # Caso decrescente normal
            if value <= good_value:
                return weight
            elif value <= neutral_value:
                return ((neutral_value - value) / (neutral_value - good_value)) * weight
            else:
                denominator = neutral_value if neutral_value != 0 else 1
                return -((abs(value - neutral_value)) / abs(denominator)) * weight
        elif good_value > neutral_value:  # Caso crescente incomum
            if value >= good_value:
                return weight
            elif value >= neutral_value:
                return ((good_value - value) / (good_value - neutral_value)) * weight
            else:
                denominator = neutral_value if neutral_value != 0 else 1
                return -((abs(neutral_value - value)) / abs(denominator)) * weight
        else:
            return 0

    def _calculate_string_score_value(self, value: str, column: str) -> float:
        """Calcula pontuação para um valor de string individual."""
        points_column = self.string_columns_map.get(column)

        if not points_column or points_column not in self.df.columns:
            return 0

        try:
            # Cria mapeamento de valores string para pontos
            mapping_data = self.df.iloc[5:].copy()
            mapping_data[points_column] = pd.to_numeric(mapping_data[points_column], errors='coerce')
            mapping_data = mapping_data.dropna(subset=[column, points_column])

            mapping = pd.Series(
                mapping_data[points_column].values,
                index=mapping_data[column]
            ).to_dict()

            if not mapping:
                return 0

            # Calcula pontuação base * peso
            clean_value = str(value).strip()
            base_score = mapping.get(clean_value, 0)
            column_weight = float(self.weights.get(column, 0))

            return base_score * column_weight
        except Exception as e:
            print(f"Erro ao calcular pontuação para '{column}': {str(e)}")
            return 0

    def generate_visualizations(self) -> None:
        """Gera todas as visualizações de análise."""
        print("\n--- Gerando Visualizações ---")

        if self.calculation_df is None:
            print("Dados não disponíveis para geração de gráficos")
            return

        try:
            self._generate_total_score_chart()
            self._generate_numeric_charts()
            self._generate_string_charts()
            self._generate_boolean_charts()
            print("--- Visualizações Geradas ---")
        except Exception as e:
            print(f"Erro ao gerar visualizações: {str(e)}")

    def _generate_total_score_chart(self) -> None:
        """Gera gráfico de barras para pontuação total."""
        if 'Total_Score' not in self.calculation_df.columns:
            print("Pontuação total não calculada. Pulando gráfico.")
            return

        max_theoretical_score = self.weights.sum() if self.weights is not None else 1.0
        print(f"  Pontuação máxima teórica: {max_theoretical_score:.2f}")

        analysis_df = self.calculation_df[
            ~self.calculation_df[self.model_column].isin(['BOM', 'NEUTRO'])
        ].copy()

        analysis_df.dropna(subset=['Total_Score'], inplace=True)

        if analysis_df.empty:
            print("Nenhum dado válido para plotar")
            return

        # Ordena e classifica por pontuação
        analysis_df = analysis_df.sort_values('Total_Score', ascending=False)
        analysis_df['Color_Category'] = analysis_df['Total_Score'].apply(
            lambda x: 'Positiva' if x >= 0 else 'Negativa'
        )

        # Cria gráfico
        fig = px.bar(
            analysis_df,
            x='Total_Score',
            y=self.model_column,
            orientation='h',
            color='Color_Category',
            color_discrete_map={'Positiva': 'lightgreen', 'Negativa': 'palevioletred'},
            hover_name=self.model_column,
            hover_data={'Total_Score': ':.2f'},
            title='Pontuação Total dos Modelos'
        )

        # Configurações de layout
        fig.update_layout(
            yaxis={'categoryorder': 'total ascending'},
            plot_bgcolor='white',
            paper_bgcolor='white',
            legend_title_text='Resultado',
            xaxis_title='Pontuação Total',
            yaxis_title='Modelo'
        )

        # Adiciona linhas de referência
        fig.add_vline(x=0, line_dash='dash', line_color='black')
        fig.add_vline(x=max_theoretical_score, line_dash='dash', line_color='black')

        # Adiciona anotações
        self._add_reference_annotation(
            fig, max_theoretical_score, len(analysis_df),
            "Desejável (BOM)<br>(NEUTRO)"
        )
        self._add_reference_annotation(
            fig, 0, len(analysis_df),
            "Mínimo Aceitável<br>(NEUTRO)"
        )

        # Adiciona anotação para melhor produto
        if not analysis_df.empty:
            best_product = analysis_df.iloc[0]
            fig.add_annotation(
                x=best_product['Total_Score'],
                y=best_product[self.model_column],
                text="🏆 Melhor Produto",
                showarrow=False,
                font=dict(color="#00008B", size=12),
                bgcolor="white",
                bordercolor="black",
                borderwidth=1,
                borderpad=4,
                xshift=-15,
                yshift=25
            )

        fig.show()

    def _add_reference_annotation(
        self,
        fig: go.Figure,
        x_value: float,
        y_position: int,
        text: str
    ) -> None:
        """Adiciona anotação de referência ao gráfico."""
        fig.add_annotation(
            x=x_value,
            y=y_position - 1,
            xref="x",
            yref="y",
            text=text,
            showarrow=True,
            font=dict(size=16, color="#000000"),
            arrowhead=2,
            arrowsize=1,
            arrowwidth=2,
            arrowcolor="#636363",
            ax=0,
            ay=-45,
            bordercolor="#c7c7c7",
            borderwidth=2,
            borderpad=4,
            bgcolor='white',
            opacity=1
        )

    def _generate_numeric_charts(self) -> None:
        """Gera gráficos para colunas numéricas."""
        if self.data_types is None:
            return

        numeric_cols = [
            col for col in self.data_types.index
            if self.data_types[col] == 'number' and col in self.calculation_df.columns
        ]

        for col in numeric_cols:
            print(f"Gerando gráfico para coluna numérica: '{col}'")

            # Prepara dados
            df = self.calculation_df[
                ~self.calculation_df[self.model_column].isin(['BOM', 'NEUTRO'])
            ][[self.model_column, col]].copy()

            df.dropna(subset=[col], inplace=True)

            if df.empty:
                continue

            # Obtém valores de referência
            good_value = self.good_values.get(col)
            neutral_value = self.neutral_values.get(col)
            is_inverse = self.proportionality.get(col, '').lower() == 'i_proportional'

            # Classifica valores
            df['Color_Category'] = df.apply(
                lambda x: self._classify_numeric_value(
                    x[col], good_value, neutral_value, is_inverse
                ),
                axis=1
            )

            # Ordena
            df = df.sort_values(col, ascending=not is_inverse)

            # Cria gráfico
            fig = px.bar(
                df,
                x=col,
                y=self.model_column,
                orientation='h',
                color='Color_Category',
                color_discrete_map={
                    'Positiva': 'lightgreen',
                    'Negativa': 'palevioletred',
                    'Neutra': 'lightgray'
                },
                hover_name=self.model_column,
                hover_data={col: ':.2f'},
                title=f"{col} {'(Inversamente Proporcional)' if is_inverse else ''}"
            )

            # Configura layout
            fig.update_layout(
                plot_bgcolor='white',
                paper_bgcolor='white',
                legend_title_text='Resultado',
                xaxis_title=col,
                yaxis_title='Modelo'
            )

            # Adiciona linhas de referência
            if pd.notna(neutral_value):
                self._add_reference_line(
                    fig, float(neutral_value), len(df),
                    "Mínimo Aceitável<br>(NEUTRO)",
                    is_inverse
                )
            if pd.notna(good_value):
                self._add_reference_line(
                    fig, float(good_value), len(df),
                    "Desejável (BOM)",
                    is_inverse
                )

            fig.show()

    def _classify_numeric_value(
        self,
        value: float,
        good_value: float,
        neutral_value: float,
        is_inverse: bool
    ) -> str:
        """Classifica um valor numérico como Positivo, Negativo ou Neutro."""
        if pd.isna(neutral_value):
            return 'Neutra'

        value = float(value)
        neutral_value = float(neutral_value)

        if is_inverse:
            return 'Positiva' if value <= neutral_value else 'Negativa'
        else:
            return 'Positiva' if value >= neutral_value else 'Negativa'

    def _add_reference_line(
        self,
        fig: go.Figure,
        value: float,
        y_position: int,
        text: str,
        is_inverse: bool
    ) -> None:
        """Adiciona linha de referência ao gráfico numérico."""
        fig.add_vline(
            x=value,
            line_dash='dash',
            line_color='black'
        )

        fig.add_annotation(
            x=value,
            y=y_position - 1,
            text=text,
            showarrow=True,
            font=dict(size=16, color="#000000"),
            arrowhead=2,
            arrowsize=1,
            arrowwidth=2,
            arrowcolor="#636363",
            ax=0,
            ay=-45,
            bordercolor="#c7c7c7",
            borderwidth=2,
            borderpad=4,
            bgcolor='white',
            opacity=1
        )

    def _generate_string_charts(self) -> None:
        """Gera gráficos para colunas de string."""
        if self.data_types is None:
            return

        string_cols = [
            col for col in self.data_types.index
            if self.data_types.get(col) == 'string' and col in self.calculation_df.columns
        ]

        for col in string_cols:
            print(f"Gerando gráfico para string: '{col}'")
            pts_col = self.string_columns_map.get(col)

            if not pts_col or pts_col not in self.df.columns:
                continue

            try:
                # Cria mapeamento string -> pontos
                mapping_data = self.df.iloc[5:].copy()
                mapping_data[pts_col] = pd.to_numeric(mapping_data[pts_col], errors='coerce')
                mapping_data = mapping_data.dropna(subset=[col, pts_col])

                string_mapping = pd.Series(
                    mapping_data[pts_col].values,
                    index=mapping_data[col]
                ).to_dict()

                if not string_mapping:
                    continue

                # Prepara dados para plotagem
                df = self.calculation_df[
                    ~self.calculation_df[self.model_column].isin(['BOM', 'NEUTRO'])
                ][[self.model_column, col]].copy()

                df['BaseValue'] = df[col].map(string_mapping).fillna(0)
                df = df.sort_values('BaseValue', ascending=False)
                df['Position'] = range(len(df))

                # Cria gráfico
                fig = px.scatter(
                    df,
                    x='Position',
                    y='BaseValue',
                    color=col,
                    hover_name=self.model_column,
                    title=f'Comparação de {col.capitalize()} entre Modelos (Pontuação Base)',
                    size_max=15,
                    hover_data={'Position': False, 'BaseValue': True, col: True},
                    labels={
                        'BaseValue': 'Pontuação Base (do CSV)',
                        col: col.capitalize()
                    }
                )

                # Adiciona linhas de referência
                good_str = self.good_values.get(col)
                neutral_str = self.neutral_values.get(col)
                good_base = string_mapping.get(good_str)
                neutral_base = string_mapping.get(neutral_str)

                if good_base is not None:
                    fig.add_hline(
                        y=good_base,
                        line_dash='dash',
                        line_color='green',
                        line_width=2,
                        annotation_text=f"BOM: '{good_str}' ({good_base:.2f})",
                        annotation_position="top right",
                        annotation_font=dict(color='green', size=12)
                    )

                if neutral_base is not None:
                    fig.add_hline(
                        y=neutral_base,
                        line_dash='dash',
                        line_color='orange',
                        line_width=2,
                        annotation_text=f"NEUTRO: '{neutral_str}' ({neutral_base:.2f})",
                        annotation_position="bottom right",
                        annotation_font=dict(color='orange', size=12)
                    )

                # Configura layout
                fig.update_layout(
                    xaxis=dict(
                        title='Modelos Ordenados por Pontuação Base',
                        showticklabels=False,
                        showgrid=False,
                        zeroline=False
                    ),
                    yaxis=dict(
                        title='Pontuação Base (Definida no CSV)',
                        showgrid=True,
                        gridcolor='lightgray',
                        zeroline=True,
                        zerolinecolor='lightgray'
                    ),
                    plot_bgcolor='white',
                    paper_bgcolor='white',
                    margin=dict(l=40, r=40, t=60, b=40),
                    legend=dict(
                        title_text=col.capitalize(),
                        orientation='h',
                        yanchor='bottom',
                        y=-0.3,
                        xanchor='center',
                        x=0.5
                    ),
                    hoverlabel=dict(
                        bgcolor='white',
                        font_size=12,
                        font_family='Arial'
                    )
                )

                fig.update_traces(
                    marker=dict(
                        size=12,
                        line=dict(width=1, color='DarkSlateGrey'),
                        opacity=0.8
                    )
                )

                fig.show()
            except Exception as e:
                print(f"Erro ao gerar gráfico para '{col}': {str(e)}")

    def _generate_boolean_charts(self) -> None:
        """Gera gráficos para colunas booleanas."""
        if self.data_types is None:
            return

        bool_cols = [
            col for col in self.data_types.index
            if self.data_types[col] == 'boolean' and col in self.calculation_df.columns
        ]

        for col in bool_cols:
            df = self.calculation_df[
                ~self.calculation_df[self.model_column].isin(['BOM', 'NEUTRO'])
            ][[self.model_column, col]].copy()

            df['Value'] = df[col].map({True: 1, False: 0})
            df['Size'] = 20

            fig = px.scatter(
                df,
                x=self.model_column,
                y='Value',
                color=col,
                color_discrete_map={True: '#4CAF50', False: '#F44336'},
                size='Size',
                title=f'{col} por Modelo',
                hover_name=self.model_column,
                hover_data={'Value': False, 'Size': False},
                category_orders={col: [True, False]}
            )

            # Atualiza a legenda
            fig.for_each_trace(
                lambda t: t.update(name='SIM' if t.name == 'True' else 'NÃO')
            )

            # Configura eixos
            fig.update_yaxes(
                range=[-0.5, 1.5],
                tickvals=[0, 1],
                ticktext=['Não', 'Sim'],
                showgrid=False
            )

            # Adiciona linhas de referência
            fig.add_hline(y=1, line_dash='dash', line_color='green')
            fig.add_hline(y=0, line_dash='dash', line_color='orange')

            # Configura layout
            fig.update_layout(
                xaxis_title=None,
                yaxis_title=None,
                plot_bgcolor='white',
                paper_bgcolor='white'
            )

            fig.show()

    def recommend_products(self) -> None:
        """Recomenda produtos com base na análise realizada."""
        if 'Total_Score' not in self.calculation_df.columns:
            print("Pontuação total não calculada. Não é possível recomendar.")
            return

        products = self.calculation_df[
            ~self.calculation_df[self.model_column].isin(['BOM', 'NEUTRO'])
        ]

        if products.empty:
            print("Nenhum produto encontrado para recomendação.")
            return

        max_score = products['Total_Score'].max()

        if pd.isna(max_score):
            print("Não foi possível determinar a pontuação máxima.")
            return

        recommended = products[products['Total_Score'] == max_score]

        print("\n--- Produtos Recomendados ---")

        if recommended.empty:
            print("Nenhum produto atingiu a pontuação máxima.")
            return

        for _, product in recommended.iterrows():
            self._print_product_recommendation(product)

    def _print_product_recommendation(self, product: pd.Series) -> None:
        """Imprime detalhes da recomendação de um produto."""
        print(f"\nProduto: {product[self.model_column]} com pontuação total de {product['Total_Score']:.2f}")
        print("Detalhes da Pontuação por Critério (Ordenado por Peso):")

        # Ordena critérios por peso
        sorted_criteria = sorted(
            [(col, self.weights[col]) for col in self.weights.index if col in self.weights],
            key=lambda x: x[1], reverse=True
        )

        for col, weight in sorted_criteria:
            score_col = f"{col}_score"

            if score_col not in product or pd.isna(product[score_col]):
                continue

            score = product[score_col]
            current_value = product.get(col, "N/A")
            dtype = self.data_types.get(col, "desconhecido")

            self._print_criterion_details(col, weight, score, current_value, dtype)

    def _print_criterion_details(
        self,
        criterion: str,
        weight: float,
        score: float,
        current_value: Union[str, float, bool],
        dtype: str
    ) -> None:
        """Imprime detalhes de um critério individual."""
        justification = f"(Peso: {weight:.2f}, Pontos: {score:.2f})"

        if dtype == 'string':
            value_str = f"'{current_value}'" if current_value != "N/A" else current_value
            if score > 0:
                print(f"  - {criterion}: {value_str} [Vantagem] {justification}")
            elif score < 0:
                print(f"  - {criterion}: {value_str} [Desvantagem] {justification}")
            else:
                print(f"  - {criterion}: {value_str} [Neutro] {justification}")

        elif dtype == 'boolean':
            value_str = self._format_boolean_value(current_value)
            if score > 0:
                print(f"  - {criterion}: {value_str} [Vantagem] {justification}")
            elif score < 0:
                print(f"  - {criterion}: {value_str} [Desvantagem] {justification}")
            else:
                print(f"  - {criterion}: {value_str} [Neutro] {justification}")

        elif dtype == 'number':
            value_str = self._format_numeric_value(current_value, criterion)
            if score >= weight * 0.99:
                print(f"  - {criterion}: {value_str} [Ótimo] {justification}")
            elif score > 0:
                print(f"  - {criterion}: {value_str} [Bom] {justification}")
            elif score == 0:
                print(f"  - {criterion}: {value_str} [Neutro] {justification}")
            else:
                print(f"  - {criterion}: {value_str} [Abaixo do Neutro] {justification}")
        else:
            print(f"  - {criterion}: {current_value} [Tipo Desconhecido] {justification}")

    def _format_boolean_value(self, value: Union[bool, str]) -> str:
        """Formata valor booleano para exibição."""
        if value is True:
            return "Sim"
        elif value is False:
            return "Não"
        else:
            return "N/A"

    def _format_numeric_value(self, value: Union[float, str], column: str) -> str:
        """Formata valor numérico para exibição com referências."""
        if isinstance(value, (int, float)):
            value_str = f"{value:.1f}"
        else:
            value_str = str(value)

        good_value = self.good_values.get(column)
        neutral_value = self.neutral_values.get(column)

        if pd.notna(good_value) and pd.notna(neutral_value):
            value_str += f" (Bom: {float(good_value):.1f}, Neutro: {float(neutral_value):.1f})"

        return value_str

def analyze_electronics_data(file_path: str = 'base_eletronicos_2.csv') -> None:
    """Executa análise completa para dados de eletrônicos."""
    try:
        print("--- Análise para base de eletrônicos ---")
        analyzer = DataAnalyzer(file_path)
        analyzer.load_and_prepare_data()
        analyzer.calculate_scores()
        analyzer.generate_visualizations()
        analyzer.recommend_products()
    except FileNotFoundError:
        print("\nErro: Arquivo não encontrado.")
    except Exception as e:
        print(f"\nOcorreu um erro inesperado: {str(e)}")


if __name__ == "__main__":
    analyze_electronics_data()