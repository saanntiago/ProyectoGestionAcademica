-- =========================================================================
-- schema.sql
-- Base de datos relacional del Proyecto Integrador de Gestión Académica.
--
-- Motor: MySQL 8 / MariaDB (XAMPP)
-- Base:  bd_universidad (la misma de las prácticas anteriores)
--
-- Qué hace este script:
--   1. Crea la base de datos y las tablas si no existen (es idempotente:
--      se puede ejecutar varias veces sin borrar información).
--   2. Agrega la tabla USUARIO, necesaria para la autenticación de la
--      aplicación web (las contraseñas se guardan con hash bcrypt).
--   3. Carga datos de ejemplo solo si las tablas están vacías (INSERT IGNORE).
--
-- Cómo ejecutarlo:
--   Opción A (consola de XAMPP):
--       C:\xampp\mysql\bin\mysql.exe -u root < schema.sql
--   Opción B: abrir este archivo en MySQL Workbench o phpMyAdmin y ejecutarlo.
--
-- Aplica conceptos de Teoría de Bases de Datos:
--   llaves primarias, llaves foráneas, restricciones UNIQUE,
--   integridad referencial y borrado en cascada (ON DELETE CASCADE).
-- =========================================================================

CREATE DATABASE IF NOT EXISTS bd_universidad
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

USE bd_universidad;

-- -------------------------------------------------------------------------
-- 1. TABLAS DEL NEGOCIO
-- -------------------------------------------------------------------------

-- Catálogo de carreras (programas académicos).
CREATE TABLE IF NOT EXISTS CARRERA (
  IdCarrera INT NOT NULL AUTO_INCREMENT,
  NombreCarrera VARCHAR(100) NOT NULL,
  PRIMARY KEY (IdCarrera)
) ENGINE = InnoDB;

-- Datos personales del estudiante.
-- FechaNacimiento permite calcular la edad con TIMESTAMPDIFF.
CREATE TABLE IF NOT EXISTS ESTUDIANTE (
  IdEstudiante INT NOT NULL AUTO_INCREMENT,
  PrimerNombre VARCHAR(50) NOT NULL,
  SegundoNombre VARCHAR(50) NULL,
  PrimerApellido VARCHAR(50) NOT NULL,
  SegundoApellido VARCHAR(50) NULL,
  NumeroTel VARCHAR(20) NULL,
  CorreoElectronico VARCHAR(100) NOT NULL UNIQUE,
  Direccion VARCHAR(50) NULL,
  FechaNacimiento DATE NOT NULL,
  IdCarrera INT NOT NULL,
  PRIMARY KEY (IdEstudiante),
  CONSTRAINT fk_estudiante_carrera
    FOREIGN KEY (IdCarrera) REFERENCES CARRERA (IdCarrera)
    ON DELETE RESTRICT ON UPDATE CASCADE
) ENGINE = InnoDB;

-- Docentes de la universidad.
CREATE TABLE IF NOT EXISTS PROFESOR (
  IdProfesor INT NOT NULL AUTO_INCREMENT,
  PrimerNombre VARCHAR(50) NOT NULL,
  SegundoNombre VARCHAR(50) NULL,
  PrimerApellido VARCHAR(50) NOT NULL,
  SegundoApellido VARCHAR(50) NULL,
  NumeroTel VARCHAR(20) NULL,
  CorreoElectronico VARCHAR(100) NOT NULL UNIQUE,
  Direccion VARCHAR(50) NULL,
  Edad INT NULL,
  Especialidad VARCHAR(50) NULL,
  PRIMARY KEY (IdProfesor)
) ENGINE = InnoDB;

-- Asignaturas que pertenecen a una carrera.
CREATE TABLE IF NOT EXISTS MATERIA (
  IdMateria INT NOT NULL AUTO_INCREMENT,
  NombreMateria VARCHAR(100) NOT NULL,
  Creditos INT NOT NULL,
  Semestre INT NOT NULL,
  IdCarrera INT NOT NULL,
  PRIMARY KEY (IdMateria),
  CONSTRAINT fk_materia_carrera
    FOREIGN KEY (IdCarrera) REFERENCES CARRERA (IdCarrera)
    ON DELETE RESTRICT ON UPDATE CASCADE
) ENGINE = InnoDB;

-- Oferta académica: un curso es una materia abierta en un periodo.
CREATE TABLE IF NOT EXISTS CURSO (
  IdCurso INT NOT NULL AUTO_INCREMENT,
  NombreCurso VARCHAR(100) NOT NULL,
  PeriodoAcademico VARCHAR(10) NOT NULL,
  Cupos INT NOT NULL,
  IdMateria INT NOT NULL,
  Aula VARCHAR(30) NOT NULL,
  Horario VARCHAR(100) NOT NULL,
  PRIMARY KEY (IdCurso),
  CONSTRAINT fk_curso_materia
    FOREIGN KEY (IdMateria) REFERENCES MATERIA (IdMateria)
    ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE = InnoDB;

-- Relación N:M entre profesores y cursos.
CREATE TABLE IF NOT EXISTS PROFESOR_CURSO (
  IdProfesor INT NOT NULL,
  IdCurso INT NOT NULL,
  PRIMARY KEY (IdProfesor, IdCurso),
  CONSTRAINT fk_profesor_curso_profesor
    FOREIGN KEY (IdProfesor) REFERENCES PROFESOR (IdProfesor)
    ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT fk_profesor_curso_curso
    FOREIGN KEY (IdCurso) REFERENCES CURSO (IdCurso)
    ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE = InnoDB;

-- Cabecera de la matrícula: quién se matricula, cuándo y cuánto paga.
CREATE TABLE IF NOT EXISTS MATRICULA (
  IdMatricula INT NOT NULL AUTO_INCREMENT,
  Fecha DATE NOT NULL,
  Estado VARCHAR(20) NOT NULL,
  IdEstudiante INT NOT NULL,
  Valor INT NOT NULL,
  PRIMARY KEY (IdMatricula),
  CONSTRAINT fk_matricula_estudiante
    FOREIGN KEY (IdEstudiante) REFERENCES ESTUDIANTE (IdEstudiante)
    ON DELETE RESTRICT ON UPDATE CASCADE
) ENGINE = InnoDB;

-- Detalle de la matrícula: cursos inscritos y nota final de cada uno.
-- La llave primaria compuesta (IdMatricula, IdCurso) impide duplicados.
CREATE TABLE IF NOT EXISTS DETALLE_MATRICULA (
  IdMatricula INT NOT NULL,
  IdCurso INT NOT NULL,
  NotaFinal DECIMAL(4,2) NULL,
  Estado VARCHAR(20) NULL,
  PRIMARY KEY (IdMatricula, IdCurso),
  CONSTRAINT fk_detalle_matricula_matricula
    FOREIGN KEY (IdMatricula) REFERENCES MATRICULA (IdMatricula)
    ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT fk_detalle_matricula_curso
    FOREIGN KEY (IdCurso) REFERENCES CURSO (IdCurso)
    ON DELETE RESTRICT ON UPDATE CASCADE
) ENGINE = InnoDB;

-- -------------------------------------------------------------------------
-- 2. TABLA DE USUARIOS DE LA APLICACIÓN
-- -------------------------------------------------------------------------
-- Solo se guarda el HASH bcrypt de la contraseña (nunca texto plano).
-- El primer usuario se crea con "python seed.py" o desde /registro.
CREATE TABLE IF NOT EXISTS USUARIO (
  IdUsuario INT NOT NULL AUTO_INCREMENT,
  Username VARCHAR(50) NOT NULL,
  PasswordHash VARCHAR(255) NOT NULL,
  NombreCompleto VARCHAR(100) NULL,
  Rol VARCHAR(20) NOT NULL DEFAULT 'ADMIN',
  CreadoEn TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (IdUsuario),
  UNIQUE KEY uq_usuario_username (Username)
) ENGINE = InnoDB;

-- -------------------------------------------------------------------------
-- 3. DATOS DE EJEMPLO (solo se insertan si no existen)
-- -------------------------------------------------------------------------

INSERT IGNORE INTO CARRERA (IdCarrera, NombreCarrera) VALUES
(1, 'Ingeniería de Sistemas'),
(2, 'Administración de Empresas'),
(3, 'Contaduría Pública'),
(4, 'Diseño Gráfico'),
(5, 'Ingeniería Industrial');

INSERT IGNORE INTO ESTUDIANTE
(IdEstudiante, PrimerNombre, SegundoNombre, PrimerApellido, SegundoApellido,
 NumeroTel, CorreoElectronico, Direccion, FechaNacimiento, IdCarrera)
VALUES
(1, 'Ana', 'María', 'Gómez', 'López', '3001112233',
 'ana.gomez@correo.com', 'CRA 1 50 12', '2006-03-15', 1),
(2, 'Carlos', 'Andrés', 'Pérez', 'Ramírez', '3012223344',
 'carlos.perez@correo.com', 'CL 123 68 15', '1971-12-15', 2),
(3, 'Laura', 'Isabel', 'Torres', 'Mendoza', '3023334455',
 'laura.torres@correo.com', 'CRA 89 106 23', '1984-05-10', 3),
(4, 'Miguel', NULL, 'Rojas', 'Castro', '3034445566',
 'miguel.rojas@correo.com', 'CL 23 42 5', '1992-11-05', 4),
(5, 'Sofía', 'Valentina', 'Hernández', 'Díaz', '3045556677',
 'sofia.hernandez@correo.com', 'CL 181 7 23', '2008-01-12', 5);

INSERT IGNORE INTO PROFESOR
(IdProfesor, PrimerNombre, SegundoNombre, PrimerApellido, SegundoApellido,
 NumeroTel, CorreoElectronico, Edad, Especialidad)
VALUES
(1, 'Laura', 'Isabel', 'Martínez', 'Torres', '3101112233',
 'laura.martinez@universidad.com', 32, 'Maestría'),
(2, 'Pedro', NULL, 'Rodríguez', 'Díaz', '3112223344',
 'pedro.rodriguez@universidad.com', 56, 'Doctorado'),
(3, 'Andrés', 'Felipe', 'García', 'Moreno', '3123334455',
 'andres.garcia@universidad.com', 27, 'Maestría'),
(4, 'Camila', 'Alejandra', 'Vargas', 'Ruiz', '3134445566',
 'camila.vargas@universidad.com', 30, 'Maestría'),
(5, 'Jorge', NULL, 'Navarro', 'Silva', '3145556677',
 'jorge.navarro@universidad.com', 44, 'Doctorado');

INSERT IGNORE INTO MATERIA
(IdMateria, NombreMateria, Semestre, IdCarrera, Creditos)
VALUES
(1, 'Bases de Datos', 3, 1, 2),
(2, 'Administración Financiera', 4, 2, 1),
(3, 'Contabilidad General', 1, 3, 3),
(4, 'Diseño Digital', 2, 4, 2),
(5, 'Procesos Industriales', 5, 5, 3);

INSERT IGNORE INTO CURSO
(IdCurso, NombreCurso, PeriodoAcademico, Cupos, IdMateria, Aula, Horario)
VALUES
(1, 'Bases de Datos - Grupo A', '2026-1', 30, 1, 'A404', 'MIE - 7AM A 9AM'),
(2, 'Administración Financiera - Grupo A', '2026-1', 25, 2, 'A204', 'JUE - 7AM A 9AM'),
(3, 'Contabilidad General - Grupo A', '2026-1', 35, 3, 'A307', 'VIE - 2PM A 4PM'),
(4, 'Diseño Digital - Grupo A', '2026-1', 20, 4, 'A502', 'LUN - 8AM A 10AM'),
(5, 'Procesos Industriales - Grupo A', '2026-1', 40, 5, 'A204', 'MAR - 9AM A 11AM');

INSERT IGNORE INTO PROFESOR_CURSO (IdProfesor, IdCurso) VALUES
(1, 1), (2, 2), (3, 3), (4, 4), (5, 5);

INSERT IGNORE INTO MATRICULA
(IdMatricula, Fecha, Estado, IdEstudiante, Valor)
VALUES
(1, '2026-01-15', 'ACTIVA', 1, 4300000),
(2, '2026-01-16', 'ACTIVA', 2, 4000000),
(3, '2026-01-17', 'FINALIZADA', 3, 300000),
(4, '2026-01-18', 'ACTIVA', 4, 23232),
(5, '2026-01-19', 'CANCELADA', 5, 23333);

INSERT IGNORE INTO DETALLE_MATRICULA
(IdMatricula, IdCurso, NotaFinal, Estado)
VALUES
(1, 1, 3.50, 'APROBADO'),
(1, 2, 5.00, NULL),
(2, 2, 2.80, NULL),
(3, 3, 4.50, NULL),
(4, 4, 1.90, NULL),
(5, 5, 3.00, NULL);

-- Fin del script.
