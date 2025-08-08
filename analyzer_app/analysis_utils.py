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
        """Carrega os dados brutos do CSV, com detecção robusta de separador e cabeçalho."""
        try:
            with open(self.file_path, 'r', encoding='UTF-8', newline='') as f:
                first_line = f.readline()
                # Retorna ao início do arquivo para leitura completa pelo Sniffer/Pandas
                f.seek(0) 
                
                # Tenta detectar o dialeto (incluindo separador)
                try:
                    dialect = csv.Sniffer().sniff(f.read(2048))
                    separator = dialect.delimiter
                except csv.Error:
                    # Fallback para vírgula se o Sniffer falhar
                    separator = ',' 
                
                f.seek(0)
                print(f"Separador '{separator}' detectado.")

                # Verifica se a primeira linha parece ser de dados ou um cabeçalho
                # Palavras-chave que indicam uma linha de dados/configuração
                config_keywords = ['PESO', 'TIPO', 'FUNCAO', 'BOM', 'NEUTRO']
                # Verifica se alguma das palavras-chave está no início da primeira linha
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
        
        # Verifica se o primeiro valor da primeira coluna é uma string (indicativo do formato novo)
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
                return # Sucesso, termina a função
            except (IndexError, ValueError) as e:
                print(f"Falha no método novo: {e}. Tentando método antigo.")

        # Se não for formato novo ou se o try falhou, usa o método antigo
        print("Extraindo configuração pelo método antigo (baseado em posição).")
        # Define as palavras-chave na primeira coluna para padronizar o dataframe
        self.df.loc[self.df.index[0], first_col] = 'PESO'
        self.df.loc[self.df.index[1], first_col] = 'TIPO'
        self.df.loc[self.df.index[2], first_col] = 'FUNCAO'
        self.df.loc[self.df.index[3], first_col] = 'BOM'
        self.df.loc[self.df.index[4], first_col] = 'NEUTRO'

        self.weights = self.df[self.df[first_col] == 'PESO'].iloc[0].drop(first_col).dropna().astype(float)
        self.data_types = self.df[self.df[first_col] == 'TIPO'].iloc[0].drop(first_col).dropna()
        self.proportionality = self.df[self.df[first_col] == 'FUNCAO'].iloc[0].drop(first_col).dropna()


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
        config_identifiers = ['PESO', 'TIPO', 'FUNCAO', 'BOM', 'NEUTRO']
        self.calculation_df = self.df[~self.df[self.model_column].isin(config_identifiers)].reset_index(drop=True)


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
        if col in self.good_values:
            self.good_values[col] = pd.to_numeric(self.good_values.get(col), errors='coerce')
        if col in self.neutral_values:
            self.neutral_values[col] = pd.to_numeric(self.neutral_values.get(col), errors='coerce')
        self.calculation_df[col] = pd.to_numeric(self.calculation_df[col], errors='coerce')

    def _convert_boolean_column(self, col: str) -> None:
        """Converte coluna booleana e valores de referência."""
        if col in self.good_values:
            self.good_values[col] = str(self.good_values.get(col, '')).strip().upper() == 'TRUE'
        if col in self.neutral_values:
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

        print(f"  Tipo: {self.data_types.get(col, 'N/A')}, Proporcionalidade: {proportionality}")
        print(f"  Valores BOM: {good_value}, NEUTRO: {neutral_value}, Peso: {weight}")

        self.calculation_df[score_col_name] = self.calculation_df.apply(
            lambda row: self._calculate_numeric_score_value(
                row.get(col), good_value, neutral_value, weight, proportionality
            ),
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
            lambda row: self._calculate_string_score_value(row.get(col), col),
            axis=1
        )

    def _show_partial_results(self, col: str, score_col_name: str) -> None:
        """Mostra resultados parciais para uma coluna."""
        if score_col_name in self.calculation_df and col in self.calculation_df:
            print(f"  Resultado parcial (Top 5):\n{self.calculation_df[[col, score_col_name]].head().to_string(index=False)}")
        else:
            print(f"  Aviso: Coluna de pontuação ou valor '{score_col_name}'/'{col}' não foi criada.")


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
        value: Union[float, bool, None],
        good_value: Union[float, bool],
        neutral_value: Union[float, bool],
        weight: float,
        proportionality_type: str
    ) -> float:
        """Calcula a pontuação para um valor numérico ou booleano individual."""
        if value is None or pd.isna(value):
            return 0
        
        if isinstance(value, (bool, np.bool_)):
            return self._calculate_boolean_score(value, good_value, neutral_value, weight)

        if pd.isna(good_value) or pd.isna(neutral_value) or pd.isna(weight):
            return 0

        if good_value == neutral_value:
            return 0

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
        if good_value > neutral_value:
            if value >= good_value: return weight
            if value >= neutral_value: return ((value - neutral_value) / (good_value - neutral_value)) * weight
            denominator = neutral_value if neutral_value != 0 else 1
            return -((abs(neutral_value - value)) / abs(denominator)) * weight
        else: # good_value < neutral_value
            if value <= good_value: return weight
            if value <= neutral_value: return ((neutral_value - value) / (neutral_value - good_value)) * weight
            denominator = neutral_value if neutral_value != 0 else 1
            return -((abs(value - neutral_value)) / abs(denominator)) * weight

    def _calculate_inverse_proportional_score(
        self,
        value: float,
        good_value: float,
        neutral_value: float,
        weight: float
    ) -> float:
        """Calcula pontuação inversamente proporcional."""
        # A lógica é a mesma da proporcional, mas com os sinais invertidos para a relação
        return self._calculate_proportional_score(value, neutral_value, good_value, weight)

    def _calculate_string_score_value(self, value: Any, column: str) -> float:
        """Calcula pontuação para um valor de string individual."""
        if pd.isna(value):
            return 0
            
        points_column = self.string_columns_map.get(column)

        if not points_column or points_column not in self.df.columns:
            return 0

        try:
            config_identifiers = ['PESO', 'TIPO', 'FUNCAO', 'BOM', 'NEUTRO']
            # Usa o DataFrame original (self.df) para criar o mapeamento
            mapping_data = self.df[~self.df[self.model_column].isin(config_identifiers)].copy()

            mapping_data[points_column] = pd.to_numeric(mapping_data[points_column], errors='coerce')
            mapping_data = mapping_data.dropna(subset=[column, points_column])
            
            mapping = pd.Series(mapping_data[points_column].values, index=mapping_data[column]).to_dict()

            if not mapping: return 0

            clean_value = str(value).strip()
            base_score = mapping.get(clean_value, 0)
            column_weight = float(self.weights.get(column, 0))

            return base_score * column_weight
        except Exception as e:
            print(f"Erro ao calcular pontuação para '{column}': {str(e)}")
            return 0

    def generate_visualizations(self) -> Dict[str, str]:
        """Gera todas as visualizações de análise e retorna como dicionário de HTML."""
        visualizations = {}
        
        if self.calculation_df is None:
            print("Dados não disponíveis para geração de gráficos")
            return visualizations

        try:
            visualizations['total_score'] = self._generate_total_score_chart()
            numeric_charts = self._generate_numeric_charts()
            visualizations.update(numeric_charts)
            string_charts = self._generate_string_charts()
            visualizations.update(string_charts)
            boolean_charts = self._generate_boolean_charts()
            visualizations.update(boolean_charts)
        except Exception as e:
            print(f"Erro ao gerar visualizações: {str(e)}")
        
        return visualizations

    def _generate_total_score_chart(self) -> str:
        """Gera gráfico de barras para pontuação total e retorna como HTML."""
        if 'Total_Score' not in self.calculation_df.columns:
            return "<div>Pontuação total não disponível</div>"

        max_theoretical_score = self.weights.sum() if self.weights is not None else 1.0
        analysis_df = self.calculation_df.copy()
        analysis_df.dropna(subset=['Total_Score'], inplace=True)

        if analysis_df.empty:
            return "<div>Nenhum dado válido para pontuação total</div>"

        analysis_df = analysis_df.sort_values('Total_Score', ascending=False)
        analysis_df['Color_Category'] = analysis_df['Total_Score'].apply(lambda x: 'Positiva' if x >= 0 else 'Negativa')

        fig = px.bar(
            analysis_df, x='Total_Score', y=self.model_column, orientation='h',
            color='Color_Category', color_discrete_map={'Positiva': 'lightgreen', 'Negativa': 'palevioletred'},
            hover_name=self.model_column, hover_data={'Total_Score': ':.2f'},
            title='Pontuação Total dos Modelos'
        )
        fig.update_layout(
            yaxis={'categoryorder': 'total ascending'}, plot_bgcolor='white', paper_bgcolor='white',
            legend_title_text='Resultado', xaxis_title='Pontuação Total', yaxis_title='Modelo'
        )
        fig.add_vline(x=0, line_dash='dash', line_color='black')
        fig.add_vline(x=max_theoretical_score, line_dash='dash', line_color='black')
        
        if not analysis_df.empty:
            self._add_reference_annotation(fig, max_theoretical_score, len(analysis_df), "Desejável (BOM)")
            self._add_reference_annotation(fig, 0, len(analysis_df), "Mínimo Aceitável (NEUTRO)")

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
            font=dict(size=14, color="#000000"), arrowhead=2, arrowsize=1, arrowwidth=2,
            arrowcolor="#636363", ax=0, ay=-40, bordercolor="#c7c7c7", borderwidth=2,
            borderpad=4, bgcolor='white', opacity=0.9
        )

    def _generate_numeric_charts(self) -> Dict[str, str]:
        """Gera gráficos para colunas numéricas e retorna como dicionário de HTML."""
        charts = {}
        if self.data_types is None: return charts

        numeric_cols = [c for c in self.data_types.index if self.data_types.get(c) == 'number' and c in self.calculation_df.columns]
        for col in numeric_cols:
            df = self.calculation_df[[self.model_column, col]].copy().dropna(subset=[col])
            if df.empty: continue

            good_value = self.good_values.get(col)
            neutral_value = self.neutral_values.get(col)
            is_inverse = self.proportionality.get(col, '') == 'i_proportional'
            
            df['Color_Category'] = df.apply(lambda x: self._classify_numeric_value(x[col], good_value, neutral_value, is_inverse), axis=1)
            df = df.sort_values(by=col, ascending=is_inverse) # Ordem inversa se for i_proporcional

            fig = px.bar(
                df, x=col, y=self.model_column, orientation='h', color='Color_Category',
                color_discrete_map={'Positiva': 'lightgreen', 'Negativa': 'palevioletred', 'Neutra': 'lightgray'},
                title=f"{col} {'(menor é melhor)' if is_inverse else '(maior é melhor)'}"
            )
            fig.update_layout(plot_bgcolor='white', paper_bgcolor='white', yaxis={'categoryorder':'total ascending'})
            
            if pd.notna(neutral_value): fig.add_vline(x=float(neutral_value), line_dash='dash', annotation_text="NEUTRO")
            if pd.notna(good_value): fig.add_vline(x=float(good_value), line_dash='dash', annotation_text="BOM")

            charts[f'numeric_{col}'] = fig.to_html(full_html=False, include_plotlyjs='cdn')
        return charts

    def _classify_numeric_value(self, value: float, good_value: Optional[float], neutral_value: Optional[float], is_inverse: bool) -> str:
        """Classifica um valor numérico para coloração do gráfico."""
        if neutral_value is None or pd.isna(value): return 'Neutra'
        
        if is_inverse: # Menor é melhor
            return 'Positiva' if value <= neutral_value else 'Negativa'
        else: # Maior é melhor
            return 'Positiva' if value >= neutral_value else 'Negativa'

    def _generate_string_charts(self) -> Dict[str, str]:
        """Gera gráficos para colunas de string e retorna como dicionário de HTML."""
        charts = {}
        if self.data_types is None: return charts

        string_cols = [c for c in self.data_types.index if self.data_types.get(c) == 'string' and c in self.calculation_df.columns]
        for col in string_cols:
            pts_col = self.string_columns_map.get(col)
            if not pts_col or pts_col not in self.df.columns: continue

            try:
                mapping_data = self.df.copy()
                mapping_data[pts_col] = pd.to_numeric(mapping_data[pts_col], errors='coerce')
                string_mapping = mapping_data.dropna(subset=[col, pts_col]).set_index(col)[pts_col].to_dict()
                if not string_mapping: continue

                df_plot = self.calculation_df[[self.model_column, col]].copy()
                df_plot['BaseValue'] = df_plot[col].map(string_mapping).fillna(0)
                df_plot = df_plot.sort_values('BaseValue', ascending=False)

                fig = px.bar(
                    df_plot, x='BaseValue', y=self.model_column, orientation='h',
                    hover_name=self.model_column, color=col, title=f'Pontuação Base para {col}'
                )
                fig.update_layout(yaxis={'categoryorder':'total ascending'}, plot_bgcolor='white', paper_bgcolor='white')
                charts[f'string_{col}'] = fig.to_html(full_html=False, include_plotlyjs='cdn')
            except Exception as e:
                print(f"Erro ao gerar gráfico para string '{col}': {e}")
        return charts

    def _generate_boolean_charts(self) -> Dict[str, str]:
        """Gera gráficos para colunas booleanas e retorna como dicionário de HTML."""
        charts = {}
        if self.data_types is None: return charts

        bool_cols = [c for c in self.data_types.index if self.data_types.get(c) == 'boolean' and c in self.calculation_df.columns]
        for col in bool_cols:
            df_counts = self.calculation_df[col].value_counts().reset_index()
            df_counts.columns = [col, 'count']
            
            fig = px.pie(
                df_counts, names=col, values='count', title=f'Distribuição de {col}',
                color=col, color_discrete_map={True: '#4CAF50', False: '#F44336'}
            )
            charts[f'boolean_{col}'] = fig.to_html(full_html=False, include_plotlyjs='cdn')
        return charts

    def recommend_products(self) -> None:
        """Recomenda produtos com base na análise realizada."""
        if 'Total_Score' not in self.calculation_df.columns:
            print("Pontuação total não calculada. Não é possível recomendar.")
            return

        products = self.calculation_df[~self.calculation_df[self.model_column].isin(['BOM', 'NEUTRO'])]
        if products.empty: return

        max_score = products['Total_Score'].max()
        if pd.isna(max_score): return

        recommended = products[products['Total_Score'] == max_score]
        print("\n--- Produtos Recomendados ---")
        for _, product in recommended.iterrows():
            self._print_product_recommendation(product)

    def _print_product_recommendation(self, product: pd.Series) -> None:
        """Imprime detalhes da recomendação de um produto."""
        print(f"\nProduto: {product[self.model_column]} com pontuação total de {product['Total_Score']:.2f}")
        print("Detalhes da Pontuação por Critério (Ordenado por Peso):")

        if self.weights is None: return
        sorted_criteria = self.weights.sort_values(ascending=False).index

        for col in sorted_criteria:
            score_col = f"{col}_score"
            if score_col not in product or pd.isna(product[score_col]): continue
            
            score = product[score_col]
            current_value = product.get(col, "N/A")
            dtype = self.data_types.get(col, "desconhecido")
            self._print_criterion_details(col, self.weights[col], score, current_value, dtype)

    def _print_criterion_details(self, criterion: str, weight: float, score: float, current_value: Any, dtype: str) -> None:
        """Imprime detalhes de um critério individual."""
        justification = f"(Peso: {weight:.2f}, Pontos: {score:.2f})"
        
        if dtype == 'number':
            good_val = self.good_values.get(criterion, "N/A")
            neutral_val = self.neutral_values.get(criterion, "N/A")
            value_str = f"{current_value} (Bom: {good_val}, Neutro: {neutral_val})"
            if score >= weight * 0.99: print(f"  - {criterion}: {value_str} [Ótimo] {justification}")
            elif score > 0: print(f"  - {criterion}: {value_str} [Bom] {justification}")
            else: print(f"  - {criterion}: {value_str} [Abaixo do Neutro] {justification}")
        else: # Boolean ou String
            if score > 0: print(f"  - {criterion}: {current_value} [Vantagem] {justification}")
            elif score < 0: print(f"  - {criterion}: {current_value} [Desvantagem] {justification}")
            else: print(f"  - {criterion}: {current_value} [Neutro] {justification}")


def analyze_data(file_path: str) -> Dict:
    """Função principal para executar a análise completa e retornar os resultados."""
    try:
        analyzer = DataAnalyzer(file_path)
        analyzer.load_and_prepare_data()
        analyzer.calculate_scores()
        visualizations = analyzer.generate_visualizations()
        
        # Aqui você pode adicionar a lógica para obter a recomendação
        # e incluir no dicionário de resultados, se necessário.
        
        return {
            "visualizations": visualizations,
            "dataframe": analyzer.calculation_df.to_html(classes='table table-striped', index=False),
            "success": True
        }
    except Exception as e:
        print(f"Ocorreu um erro inesperado ao analisar {file_path}: {str(e)}")
        return {"error": str(e), "success": False}

# Adicione este método DENTRO da classe DataAnalyzer em analysis_utils.py

def get_podium_details(self) -> list:
    """
    Retorna uma lista com os detalhes dos 3 melhores produtos para o pódio.
    """
    if 'Total_Score' not in self.calculation_df.columns:
        return []

    # Ordena o DataFrame pela pontuação total
    sorted_df = self.calculation_df.sort_values('Total_Score', ascending=False)
    
    # Pega os 3 melhores (ou menos, se não houver 3)
    top_products = sorted_df.head(3)

    podium_list = []
    rank = 1
    for index, product in top_products.iterrows():
        details_list = self._get_recommendation_details(product)
        podium_list.append({
            'rank': rank,
            'name': product[self.model_column],
            'score': f"{product['Total_Score']:.2f}",
            'details': details_list
        })
        rank += 1
    
    return podium_list

def _get_recommendation_details(self, product: pd.Series) -> list:
    """
    Retorna uma lista de strings com a justificativa da pontuação de um produto.
    """
    if self.weights is None: return []

    details_list = []
    sorted_criteria = self.weights.sort_values(ascending=False).index

    for col in sorted_criteria:
        score_col = f"{col}_score"
        if score_col not in product or pd.isna(product[score_col]): continue
        
        score = product[score_col]
        current_value = product.get(col, "N/A")
        
        # Formata o valor para exibição amigável
        if isinstance(current_value, bool):
            value_str = "Sim" if current_value else "Não"
        elif isinstance(current_value, (int, float)):
            value_str = f"{current_value:.1f}"
        else:
            value_str = str(current_value)

        # Simplifica a justificativa
        justification = ""
        if score > 0:
            justification = "[Vantagem]"
        elif score < 0:
            justification = "[Desvantagem]"
        else:
            justification = "[Neutro]"

        details_list.append(f"<b>{col}:</b> {value_str} {justification} (Pontos: {score:.2f})")
    
    return details_list

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        # A função principal foi alterada para retornar um dict,
        # então o `if __name__ == '__main__':` pode precisar de ajuste
        # para imprimir os resultados de forma legível no console.
        results = analyze_data(sys.argv[1])
        if results['success']:
            print("\n--- Análise Concluída com Sucesso ---")
            # Imprime apenas o dataframe como exemplo
            # print(results['dataframe'])
        else:
            print(f"\n--- Erro na Análise ---")
            print(results['error'])
    else:
        print("Por favor, informe o caminho do arquivo CSV como argumento")