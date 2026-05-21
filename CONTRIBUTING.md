# Cómo contribuir a ERP_Web

Estas son las reglas mínimas para colaborar en este repo. Cortas, claras, no opcionales.

---

## Branches

| Branch | Propósito | Quién puede mergear |
|---|---|---|
| `main` | Producción. Vercel + Railway despliegan desde acá. | Solo via PR desde `develop` |
| `develop` | Integración. Todas las features confluyen acá. | Cualquiera (con review aprobada) |
| `feature/<nombre>` | Trabajo en una feature. Ej: `feature/modo-basico`, `feature/asistente-flotante` | El autor merge a `develop` con PR |
| `fix/<nombre>` | Bug fixes. Ej: `fix/login-mobile-overflow` | El autor merge a `develop` con PR |
| `hotfix/<nombre>` | Bug urgente directo a `main` (raro). | Requiere review obligatoria |

**Regla**: nunca hacer push directo a `main`. Está protegida.

---

## Flujo de trabajo

1. **Antes de empezar una feature**, asegurate de tener `develop` actualizada:
   ```bash
   git checkout develop
   git pull
   git checkout -b feature/mi-feature
   ```

2. **Mientras desarrollás**, commits pequeños y descriptivos:
   ```bash
   git add archivo.tsx
   git commit -m "feat: agregar toggle Básico/Avanzado al sidebar"
   ```

3. **Antes de pedir review**, integrá `develop` por si hubo cambios:
   ```bash
   git checkout develop && git pull
   git checkout feature/mi-feature
   git rebase develop      # o git merge develop si preferís
   ```

4. **Push y PR**:
   ```bash
   git push -u origin feature/mi-feature
   ```
   Luego en GitHub: New Pull Request → base `develop`, compare `feature/mi-feature` → completar template → asignar reviewer.

5. **Review**:
   - Mínimo 1 aprobación de la otra persona.
   - El autor responde comentarios y push fixes al mismo branch.
   - Cuando todo está OK, **squash & merge** a `develop` (preferido) o merge commit (si es feature grande con commits que valen la pena conservar).

6. **Deploy a producción**: cuando varias features estén en `develop` y testeadas, abrir PR de `develop` → `main`. Al mergear, Vercel + Railway despliegan automático.

---

## Commits — convención

Estilo [Conventional Commits](https://www.conventionalcommits.org/), en español o inglés (consistente dentro del repo):

```
feat: agregar modo Básico/Avanzado al sidebar
fix: corregir overflow en mobile del modal de comprobantes
docs: actualizar README con setup de Supabase
refactor: extraer lógica de OCR a hook useOcr
test: agregar tests del chatbot
chore: actualizar dependencias
```

**Mensaje claro**: el cuerpo del commit puede tener más detalle si la PR es grande. El título de la PR sigue el mismo formato.

---

## Reglas de oro (no negociables)

1. **Nunca commitear `.env`** o credenciales. El `.gitignore` ya las cubre, pero verificá con `git status` antes de cada commit.
2. **Nunca hacer push a `main` directo.** Está protegida.
3. **Tests existentes deben pasar antes de merge.** GitHub Actions corre `pytest` y `npm run build` en cada PR.
4. **Una feature = una PR.** Si la PR está creciendo demasiado (>500 líneas, >10 archivos), partila en subfeatures.
5. **Review en <24h** o avisá si vas a demorar.
6. **No tocar `Empresa 1\`** (carpeta hermana, versión desktop). Es código productivo separado.

---

## Code style

- **Python**: PEP 8 + black formatter (`black backend/`). Type hints donde tenga sentido.
- **TypeScript**: ESLint config del proyecto (Next.js default). Funcional > clases.
- **CSS**: Tailwind utility-first. Evitar CSS custom salvo para animaciones complejas.
- **Comentarios**: en español (el público del proyecto es paraguayo). Excepciones: docstrings de funciones técnicas pueden ser inglés.
- **Nombres de archivos**: kebab-case para componentes (`asistente-flotante.tsx`) o PascalCase si exporta uno solo (`AsistenteFlotante.tsx` — usamos esto, consistente con la app actual).

---

## Tests

Cada nueva feature **debería** tener al menos 1 test:
- Backend: `pytest tests/test_<modulo>.py`
- Frontend: por ahora sin framework de tests (futuro: Playwright E2E).

Si no agregás test, justificá en la PR (ej: "es un cambio puramente visual").

---

## Issues y planning

- **GitHub Issues** para cada item del roadmap (ver `PLAN_MIGRACION_V5.md` y `~/.claude/plans/`).
- **Labels**: `phase-0-setup`, `phase-1-cloud`, `phase-2-storage`, `phase-3-auth`, `phase-4-ux`, `phase-5-deploy`, `phase-6-data`, `bug`, `enhancement`, `docs`.
- **GitHub Projects**: columnas Backlog → In Progress → Review → Done. Asignar issues al proyecto al crearlas.

Antes de empezar a trabajar en algo: **autoasignate el issue** en GitHub para que la otra persona vea que lo tomaste.

---

## Comunicación

- Decisiones técnicas importantes → comentar en el issue / PR correspondiente.
- Discusiones largas → fuera de GitHub (chat directo). Lo que se decida volverlo a postear en el issue para tener registro.
- **Antes de tocar archivos compartidos** (ej: `Sidebar.tsx`, `i18n-simple.ts`) avisá en el issue para no chocar.

---

## Contacto

- **PM / Owner**: gfcar (gfcarlos04@gmail.com)
- **Repo**: https://github.com/gfcarlos04-del/ERP-WEB

¿Dudas? Abrí un issue con label `question`.
