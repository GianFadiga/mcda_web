# analyzer_app/analysis_utils.py

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
import csv
from typing import Dict, Optional, List, Union, Any

class DataAnalyzer:
    """Classe principal para análise e comparação de dados de produtos."""

    def __init__(self, file_path: str, delimiter: Optional[str] = None, color_profile: str = 'padrao'):
        """
        Inicializa o analisador.
        Args:
            file_path: Caminho para o arquivo CSV.
            delimiter: (Opcional) O separador a ser usado. Se None, será detectado.
            color_profile: O perfil de cor ('padrao', 'tritanopia', 'monocromia')
        """
        self.file_path = file_path
        self.delimiter = delimiter
        self.df = None
        self.weights = None
        self.data_types = None
        self.proportionality = None
        self.good_values = None
        self.neutral_values = None
        self.calculation_df = None
        self.string_columns_map = {}
        self.model_column = None
        
        # Configuração de Cores de Acessibilidade
        self.color_positive = '#0072B2' # Azul (Default)
        self.color_negative = '#E69F00' # Laranja (Default)
        self._set_color_palette(color_profile)

    def _set_color_palette(self, color_profile: str) -> None:
        """Define as cores Positiva e Negativa com base no perfil de acessibilidade."""
        if color_profile == 'tritanopia':
            # Paleta Vermelho/Ciano (ideal para Tritanopia)
            self.color_positive = '#D55E00' # Laranja/Vermelho
            self.color_negative = '#009E73' # Ciano/Verde
        elif color_profile == 'monocromia':
            # Paleta de Alto Contraste (ideal para Monocromia)
            self.color_positive = '#333333' # Cinza Escuro
            self.color_negative = '#BDBDBD' # Cinza Claro
        else:
            # Padrão (Azul / Laranja) - Ideal para Protanopia/Deuteranopia
            self.color_positive = '#0072B2' # Azul
            self.color_negative = '#E69F00' # Laranja

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
        """Carrega os dados brutos do CSV com fallback inteligente para separadores."""
        try:
            separator = self.delimiter
            
            # 1. Tentativa de detecção automática
            if not separator:
                with open(self.file_path, 'r', encoding='UTF-8', newline='') as f:
                    try:
                        # Lê um pedaço maior para melhorar a precisão do Sniffer
                        sample = f.read(4096)
                        dialect = csv.Sniffer().sniff(sample)
                        separator = dialect.delimiter
                    except (csv.Error, UnicodeDecodeError):
                        separator = ',' # Fallback padrão
            
            # Verifica se a primeira linha é cabeçalho de dados ou configuração
            with open(self.file_path, 'r', encoding='UTF-8', errors='ignore') as f:
                first_line = f.readline().strip()
            
            config_keywords = ['PESO', 'TIPO', 'FUNCAO']
            is_data_row = any(first_line.upper().startswith(kw) for kw in config_keywords)
            
            header_option = None if is_data_row else 0
            
            # 2. Leitura inicial com o separador detectado
            self.df = pd.read_csv(
                self.file_path, 
                sep=separator, 
                skipinitialspace=True, 
                header=header_option, 
                encoding='utf-8', 
                on_bad_lines='error'
            )
            
            # 3. VALIDAÇÃO DE SEGURANÇA (A CORREÇÃO CRÍTICA DE ANTES)
            if self.df.shape[1] < 2 and separator != ',':
                print(f"Aviso: Leitura resultou em apenas 1 coluna com separador '{separator}'. Tentando fallback para vírgula.")
                self.df = pd.read_csv(
                    self.file_path, 
                    sep=',', 
                    skipinitialspace=True, 
                    header=header_option, 
                    encoding='utf-8', 
                    on_bad_lines='error'
                )

            if is_data_row:
                self.df.columns = [f'Coluna_{i+1}' for i in range(len(self.df.columns))]
            
            if not self.df.empty:
                 self.model_column = self.df.columns[0]
            else:
                raise ValueError("Arquivo CSV está vazio.")
                
        except Exception as e:
            raise ValueError(f"Erro ao carregar ou processar arquivo: {e}")

    def _clean_empty_columns(self) -> None:
        self.df.dropna(axis=1, how='all', inplace=True)

    def _extract_configurations(self) -> None:
        if len(self.df) < 3: raise ValueError("Arquivo CSV não tem linhas de configuração suficientes.")
        first_col = self.df.columns[0]
        self.df[first_col] = self.df[first_col].astype(str)

        try:
            self.weights = self.df[self.df[first_col].str.upper() == 'PESO'].iloc[0].drop(first_col).dropna().astype(float)
            self.data_types = self.df[self.df[first_col].str.upper() == 'TIPO'].iloc[0].drop(first_col).dropna()
            self.proportionality = self.df[self.df[first_col].str.upper() == 'FUNCAO'].iloc[0].drop(first_col).dropna()
        except IndexError:
            raise ValueError("Não foi possível encontrar as linhas de configuração (PESO, TIPO, FUNCAO). Verifique o formato do CSV.")

    def _map_string_columns(self) -> None:
        self.string_columns_map = {}
        if self.data_types is None: raise ValueError("Tipos de dados não foram carregados")
        
        string_cols = [col for col, dtype in self.data_types.items() if dtype == 'string']
        for col in string_cols:
            try:
                col_idx = list(self.df.columns).index(col)
                if col_idx + 1 < len(self.df.columns):
                    pts_col_name_original = self.df.columns[col_idx + 1]
                    if self.data_types.get(pts_col_name_original) == 'pts_string' or self.proportionality.get(pts_col_name_original) == 'pts_string':
                        new_pts_col_name = f"{col}_points"
                        self.string_columns_map[col] = new_pts_col_name
                        self.df.rename(columns={pts_col_name_original: new_pts_col_name}, inplace=True)
            except (ValueError, IndexError):
                print(f"Aviso: Não foi possível mapear coluna de pontos para a coluna string '{col}'")

    def _extract_reference_values(self) -> None:
        self.df[self.model_column] = self.df[self.model_column].astype(str)
        good_row = self.df[self.df[self.model_column].str.upper() == 'BOM']
        neutral_row = self.df[self.df[self.model_column].str.upper() == 'NEUTRO']
        self.good_values = good_row.iloc[0].dropna() if not good_row.empty else pd.Series(dtype='object')
        self.neutral_values = neutral_row.iloc[0].dropna() if not neutral_row.empty else pd.Series(dtype='object')

    def _prepare_calculation_data(self) -> None:
        config_identifiers = ['PESO', 'TIPO', 'FUNCAO', 'BOM', 'NEUTRO']
        self.calculation_df = self.df[~self.df[self.model_column].str.upper().isin(config_identifiers)].reset_index(drop=True).copy()

    def _convert_data_types(self) -> None:
        for col in self.data_types.index:
            if col in self.calculation_df.columns:
                dtype = self.data_types[col]
                if dtype == 'number': self._convert_numeric_column(col)
                elif dtype == 'boolean': self._convert_boolean_column(col)

    def _convert_numeric_column(self, col: str) -> None:
        if col in self.good_values: self.good_values[col] = pd.to_numeric(self.good_values.get(col), errors='coerce')
        if col in self.neutral_values: self.neutral_values[col] = pd.to_numeric(self.neutral_values.get(col), errors='coerce')
        self.calculation_df[col] = pd.to_numeric(self.calculation_df[col], errors='coerce')

    def _convert_boolean_column(self, col: str) -> None:
        if col in self.good_values: self.good_values[col] = str(self.good_values.get(col, '')).strip().upper() == 'TRUE'
        if col in self.neutral_values: self.neutral_values[col] = str(self.neutral_values.get(col, '')).strip().upper() == 'TRUE'
        self.calculation_df[col] = self.calculation_df[col].astype(str).str.strip().str.upper().map({'TRUE': True, 'FALSE': False}).fillna(False).astype(bool)

    def calculate_scores(self) -> None:
        if self.calculation_df is None: raise ValueError("Dados de cálculo não preparados.")
        for col in self.weights.index:
            self._process_column_for_scoring(col)
        self._calculate_total_score()

    def _process_column_for_scoring(self, col: str) -> None:
        score_col_name = f"{col}_score"
        dtype = self.data_types.get(col)
        if dtype in ['number', 'boolean']: self._calculate_numeric_score(col, score_col_name)
        elif dtype == 'string': self._calculate_string_score(col, score_col_name)

    def _calculate_numeric_score(self, col: str, score_col_name: str) -> None:
        good = self.good_values.get(col); neutral = self.neutral_values.get(col)
        weight = self.weights.get(col, 0); prop = self.proportionality.get(col)
        if pd.isna(good) or pd.isna(neutral) or not prop: self.calculation_df[score_col_name] = 0; return
        
        # Normaliza a string de proporcionalidade para minúsculo e remove espaços
        prop_clean = str(prop).strip().lower()
        
        self.calculation_df[score_col_name] = self.calculation_df.apply(
            lambda row: self._calculate_numeric_score_value(row.get(col), good, neutral, weight, prop_clean), 
            axis=1
        )

    def _calculate_string_score(self, col: str, score_col_name: str) -> None:
        self.calculation_df[score_col_name] = self.calculation_df.apply(lambda row: self._calculate_string_score_value(row.get(col), col), axis=1)

    def _calculate_total_score(self) -> None:
        score_cols = [c for c in self.calculation_df.columns if c.endswith('_score')]
        self.calculation_df['Total_Score'] = self.calculation_df[score_cols].sum(axis=1) if score_cols else 0

    def _calculate_numeric_score_value(self, value, good, neutral, weight, prop) -> float:
        if pd.isna(value): return 0
        if isinstance(value, (bool, np.bool_)): return self._calculate_boolean_score(value, good, neutral, weight)
        
        # CORREÇÃO 1: Aceita 'proportional' OU 'direct'
        if prop in ['proportional', 'direct']: 
            return self._calculate_proportional_score(value, good, neutral, weight)
            
        # CORREÇÃO 2: Aceita 'i_proportional' OU 'inverse'
        if prop in ['i_proportional', 'inverse']: 
            return self._calculate_inverse_proportional_score(value, good, neutral, weight)
            
        return 0

    def _calculate_boolean_score(self, value, good, neutral, weight) -> float:
        if good == neutral: return weight if value == good else 0
        return weight if value == good else -weight if value != neutral else 0

    def _calculate_proportional_score(self, value: float, good: float, neutral: float, weight: float) -> float:
        if good == neutral: return weight if value == good else 0
        if good > neutral:
            if value >= good: return weight
            if value >= neutral: return ((value - neutral) / (good - neutral)) * weight
            denominator = neutral if neutral != 0 else 1
            return -((abs(neutral - value)) / abs(denominator)) * weight
        else:
            if value <= good: return weight
            if value <= neutral: return ((neutral - value) / (neutral - good)) * weight
            denominator = neutral if neutral != 0 else 1
            return -((abs(value - neutral)) / abs(denominator)) * weight

    def _calculate_inverse_proportional_score(self, value: float, good: float, neutral: float, weight: float) -> float:
        if good == neutral: return weight if value == good else 0
        if good < neutral:
            if value <= good: return weight
            if value <= neutral: return ((neutral - value) / (neutral - good)) * weight
            denominator = neutral if neutral != 0 else 1
            return -((abs(value - neutral)) / abs(denominator)) * weight
        else:
            if value >= good: return weight
            if value >= neutral: return ((value - good) / (neutral - good)) * weight
            denominator = neutral if neutral != 0 else 1
            return -((abs(neutral - value)) / abs(denominator)) * weight

    def _calculate_string_score_value(self, value, column) -> float:
        if pd.isna(value): return 0
        points_col = self.string_columns_map.get(column)
        if not points_col or points_col not in self.df.columns: return 0
        config_ids = ['PESO', 'TIPO', 'FUNCAO', 'BOM', 'NEUTRO']
        map_df = self.df[~self.df[self.model_column].str.upper().isin(config_ids)]
        map_df[points_col] = pd.to_numeric(map_df[points_col], errors='coerce')
        mapping = dict(zip(map_df[column], map_df[points_col]))
        base_score = mapping.get(str(value).strip(), 0)
        weight = float(self.weights.get(column, 0))
        return base_score * weight

    # ===============================================================
    # GERAÇÃO DE GRÁFICOS
    # ===============================================================
    def generate_visualizations(self) -> Dict[str, str]:
        visualizations = {}
        if self.calculation_df is None: return visualizations
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
        if 'Total_Score' not in self.calculation_df.columns: return "<div>Pontuação total não disponível</div>"
        max_theoretical_score = self.weights.sum() if self.weights is not None else 1.0
        analysis_df = self.calculation_df[~self.calculation_df[self.model_column].isin(['BOM', 'NEUTRO'])].copy()
        analysis_df.dropna(subset=['Total_Score'], inplace=True)
        if analysis_df.empty: return "<div>Nenhum dado válido para pontuação total</div>"
        analysis_df = analysis_df.sort_values('Total_Score', ascending=False)
        analysis_df['Color_Category'] = analysis_df['Total_Score'].apply(lambda x: 'Positiva' if x >= 0 else 'Negativa')
        fig = px.bar(
            analysis_df, x='Total_Score', y=self.model_column, orientation='h',
            color='Color_Category', color_discrete_map={'Positiva': self.color_positive, 'Negativa': self.color_negative},
            hover_name=self.model_column, hover_data={'Total_Score': ':.2f'}, title='Pontuação Total dos Modelos'
        )
        fig.update_layout(yaxis={'categoryorder': 'total ascending'}, plot_bgcolor='white', paper_bgcolor='white', legend_title_text='Resultado', xaxis_title='Pontuação Total', yaxis_title='Modelo')
        fig.add_vline(x=0, line_dash='dash', line_color='black')
        fig.add_vline(x=max_theoretical_score, line_dash='dash', line_color='black')
        self._add_reference_annotation(fig, max_theoretical_score, len(analysis_df), "Desejável (BOM)<br>(NEUTRO)")
        self._add_reference_annotation(fig, 0, len(analysis_df), "Mínimo Aceitável<br>(NEUTRO)")
        if not analysis_df.empty:
            best_product = analysis_df.iloc[0]
            fig.add_annotation(x=best_product['Total_Score'], y=best_product[self.model_column], text="🏆 Melhor Produto", showarrow=False, font=dict(color="#00008B", size=12), bgcolor="white", bordercolor="black", borderwidth=1, borderpad=4, xshift=-15, yshift=25)
        return fig.to_html(full_html=False, include_plotlyjs='cdn')

    def _add_reference_annotation(self, fig: go.Figure, x_value: float, y_position: int, text: str) -> None:
        fig.add_annotation(x=x_value, y=y_position - 0.5, text=text, showarrow=True, font=dict(size=14, color="#000000"), arrowhead=2, arrowsize=1, arrowwidth=2, arrowcolor="#636363", ax=0, ay=-45, bordercolor="#c7c7c7", borderwidth=2, borderpad=4, bgcolor='white', opacity=1)

    def _generate_numeric_charts(self) -> Dict[str, str]:
        charts = {}
        if self.data_types is None: return charts
        numeric_cols = [col for col in self.data_types.index if self.data_types[col] == 'number' and col in self.calculation_df.columns]
        for col in numeric_cols:
            df = self.calculation_df[~self.calculation_df[self.model_column].isin(['BOM', 'NEUTRO'])][[self.model_column, col]].copy()
            df.dropna(subset=[col], inplace=True)
            if df.empty: continue
            good_value = self.good_values.get(col)
            neutral_value = self.neutral_values.get(col)
            
            # CORREÇÃO 3: Detecta se é inverso aceitando ambos os termos (PARA COR DO GRÁFICO)
            prop_val = str(self.proportionality.get(col, '')).strip().lower()
            is_inverse = prop_val in ['i_proportional', 'inverse']
            
            df['Color_Category'] = df.apply(lambda x: self._classify_numeric_value(x[col], good_value, neutral_value, is_inverse), axis=1)
            df = df.sort_values(col, ascending=not is_inverse)
            fig = px.bar(df, x=col, y=self.model_column, orientation='h', 
                         color='Color_Category', 
                         color_discrete_map={'Positiva': self.color_positive, 'Negativa': self.color_negative, 'Neutra': 'lightgray'}, 
                         hover_name=self.model_column, hover_data={col: ':.2f'}, title=f"{col} {'(Inversamente Proporcional)' if is_inverse else ''}")
            fig.update_layout(plot_bgcolor='white', paper_bgcolor='white', legend_title_text='Resultado', xaxis_title=col, yaxis_title='Modelo')
            if pd.notna(neutral_value): self._add_reference_line(fig, float(neutral_value), len(df), "Mínimo Aceitável<br>(NEUTRO)")
            if pd.notna(good_value): self._add_reference_line(fig, float(good_value), len(df), "Desejável (BOM)")
            charts[f'numeric_{col}'] = fig.to_html(full_html=False, include_plotlyjs='cdn')
        return charts

    def _classify_numeric_value(self, value: float, good_value: float, neutral_value: float, is_inverse: bool) -> str:
        if pd.isna(neutral_value) or pd.isna(value): return 'Neutra'
        value, neutral_value = float(value), float(neutral_value)
        if is_inverse: return 'Positiva' if value <= neutral_value else 'Negativa'
        return 'Positiva' if value >= neutral_value else 'Negativa'

    def _add_reference_line(self, fig: go.Figure, value: float, y_position: int, text: str) -> None:
        fig.add_vline(x=value, line_dash='dash', line_color='black')
        fig.add_annotation(x=value, y=y_position - 0.5, text=text, showarrow=True, font=dict(size=14, color="#000000"), arrowhead=2, arrowsize=1, arrowwidth=2, arrowcolor="#636363", ax=0, ay=-45, bordercolor="#c7c7c7", borderwidth=2, borderpad=4, bgcolor='white', opacity=1)

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
                df, x=self.model_column, y='Value', color=col, 
                color_discrete_map={True: self.color_positive, False: self.color_negative},
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
    # FUNÇÕES DO PÓDIO
    # ===============================================================
    def get_podium_details(self) -> list:
        if 'Total_Score' not in self.calculation_df.columns: return []
        sorted_df = self.calculation_df.sort_values('Total_Score', ascending=False)
        top_products = sorted_df.head(3)
        podium_list = []
        for rank, (index, product) in enumerate(top_products.iterrows(), 1):
            details_list = self._get_recommendation_details(product)
            podium_list.append({'rank': rank, 'name': product[self.model_column], 'score': f"{product['Total_Score']:.2f}", 'details': details_list})
        return podium_list

    def _get_recommendation_details(self, product: pd.Series) -> list:
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
            details_list.append(f"<b>{col}:</b> {value_str} {justification} (Pontos: {score:.4f})")
        return details_list