"""Model Advertencia (penalidade gerada por devolução em atraso)."""


class Advertencia:
    def __init__(self, id_usuario, id_emprestimo, motivo, dias_suspensao=0, id_advertencia=None):
        self.id_advertencia = id_advertencia
        self.id_usuario = id_usuario
        self.id_emprestimo = id_emprestimo
        self.motivo = motivo
        self.dias_suspensao = dias_suspensao
