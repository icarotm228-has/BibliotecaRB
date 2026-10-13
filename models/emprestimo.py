"""Model Emprestimo, com a regra de prazo por tipo de usuário (RN-01)."""
from datetime import datetime, timedelta

FORMATO = "%Y-%m-%d %H:%M:%S"
PRAZOS_DIAS = {"ALUNO": 14, "PROFESSOR": 30}


def dt_para_str(dt):
    return dt.strftime(FORMATO) if dt else None


def str_para_dt(s):
    return datetime.strptime(s, FORMATO) if s else None


class Emprestimo:
    def __init__(self, id_usuario, tombo_exemplar, id_bibliotecario, data_emprestimo,
                 data_prevista_devolucao, data_devolucao_real=None, status="ATIVO", id_emprestimo=None):
        self.id_emprestimo = id_emprestimo
        self.id_usuario = id_usuario
        self.tombo_exemplar = tombo_exemplar
        self.id_bibliotecario = id_bibliotecario
        self.data_emprestimo = data_emprestimo
        self.data_prevista_devolucao = data_prevista_devolucao
        self.data_devolucao_real = data_devolucao_real
        self.status = status

    @staticmethod
    def calcular_data_devolucao(tipo_usuario, data_base=None):
        """14 dias para ALUNO, 30 dias para PROFESSOR."""
        data_base = data_base or datetime.now()
        return data_base + timedelta(days=PRAZOS_DIAS[tipo_usuario])

    def dias_de_atraso(self, agora=None):
        agora = agora or datetime.now()
        if agora <= self.data_prevista_devolucao:
            return 0
        return max(1, (agora - self.data_prevista_devolucao).days)
