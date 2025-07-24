# denunciar_rpa.ps1
Write-Host "🚨 Iniciando RPA de denúncia automática..." -ForegroundColor Red

$jsonPath = ".\urls_suspeitas.json"

if (Test-Path $jsonPath) {
    $dados = Get-Content $jsonPath | ConvertFrom-Json

    if ($dados.urls_suspeitas.Count -gt 0) {
        Write-Host "`n🔍 Links patrocinados detectados em: $($dados.suspeitas_detectadas_em)" -ForegroundColor Yellow

        foreach ($site in $dados.urls_suspeitas) {
            Write-Host "→ Dominio: $($site.dominio)" -ForegroundColor Cyan
            Write-Host "  URL:     $($site.url)" -ForegroundColor DarkGray

            # Simula a denúncia
            Start-Sleep -Milliseconds 800
            Write-Host "  📢 Denúncia simulada com sucesso!" -ForegroundColor Green
            Write-Host ""
        }
        Write-Host "✅ Todas as denúncias foram simuladas com sucesso." -ForegroundColor Green
    }
    else {
        Write-Host "✅ Nenhum link patrocinado encontrado para denunciar." -ForegroundColor Green
    }
} else {
    Write-Host "❌ Arquivo urls_suspeitas.json não encontrado!" -ForegroundColor Red
}
