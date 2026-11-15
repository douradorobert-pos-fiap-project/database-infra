# Banco PostgreSQL da Oficina

Este repositório provisiona somente o PostgreSQL gerenciado (Amazon RDS) do sandbox da aplicação Oficina. Ele cria um RDS PostgreSQL privado, seu DB subnet group e um security group dedicado. Não cria VPC, subnets, EKS, IAM, Secrets Manager, observabilidade, migrations ou recursos Kubernetes.

## Relação com a infraestrutura compartilhada

`shared-infra` deve ser aplicado primeiro. Este projeto presume que, na região configurada em `AWS_REGION`, ele já criou uma VPC com `Name=sandbox-vpc` e `Environment=sandbox`, além de subnets privadas com `Environment=sandbox` e `Type=private` (hoje `10.0.10.0/24` e `10.0.11.0/24`).

O state do Terraform é persistido no bucket indicado por `TF_STATE_BUCKET`, com a key fixa `database/terraform.tfstate`. O bucket deve existir antes do primeiro `terraform init`. Não há compartilhamento de state com a infraestrutura principal nem uso de `terraform_remote_state`; os data sources encontram a rede diretamente na AWS por tags.

O repositório compartilhado não declara um security group de nós EKS com identificação estável para reutilização. Por isso, a entrada do RDS aceita PostgreSQL apenas do CIDR da VPC descoberta. Isso permite pods e nós do EKS nas subnets privadas acessarem a porta 5432, sem regra de Internet. É uma decisão simples e adequada ao sandbox; a regra PostgreSQL não usa `0.0.0.0/0`.

## Configuração do sandbox

`terraform/environments/sandbox/terraform.tfvars` define PostgreSQL 16, `db.t4g.micro`, Single-AZ, gp3 com 20 GiB e retenção de um dia. Região, nome e usuário administrador do banco são GitHub Variables; a senha é um GitHub Secret e nunca é versionada.

## Pré-requisitos e execução local

Requer Terraform 1.10+, AWS CLI autenticada com permissões para RDS/EC2 e a infraestrutura compartilhada aplicada. Defina a senha de forma segura e execute:

```bash
export TF_VAR_db_password='senha-fornecida-com-seguranca'
export TF_VAR_db_name='oficina'
export TF_VAR_db_username='oficina_admin'
export TF_VAR_aws_region='us-east-1'
export AWS_REGION='us-east-1'
export TF_STATE_BUCKET='terraform-state-891377055171-us-east-1'
terraform -chdir=terraform fmt -check
terraform -chdir=terraform init -backend=false
terraform -chdir=terraform validate
python -m unittest discover tests -v
./scripts/plan-database.sh
```

Para aplicar conscientemente:

```bash
./scripts/apply-database.sh
```

Use `TFVARS_FILE=/caminho/arquivo.tfvars` para outro arquivo. Não coloque `db_password` em `.tfvars`.

## GitHub Actions

Configure os GitHub Secrets `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_SESSION_TOKEN` e `DB_PASSWORD`. Configure as GitHub Variables `AWS_REGION`, `TF_STATE_BUCKET`, `DB_NAME` e `DB_USERNAME`.

Pull requests executam format, init sem backend remoto, validate e testes estáticos sem acessar a AWS. Plan e apply executam somente por `workflow_dispatch`, protegidos pelo environment `sandbox`. O preflight confirma identidade, acesso ao bucket e existência da VPC compartilhada antes de planejar o RDS.

As credenciais de serviço são separadas da credencial administradora do RDS. `OS_DB_PASSWORD` e `BILLING_DB_PASSWORD` serão usados pelo Job Kubernetes de bootstrap para criar usuários e bancos exclusivos; não são usados para provisionar a instância RDS.

## Bootstrap dos bancos lógicos no EKS

O RDS é privado, portanto o runner público do GitHub não executa `psql` diretamente. Depois do apply do RDS e da criação do namespace `oficina`, obtenha `rds_endpoint` com `terraform output` e disponibilize estas variáveis apenas na sessão segura que possui acesso ao cluster:

```text
RDS_ENDPOINT, RDS_PORT, DB_NAME, DB_USERNAME, DB_PASSWORD
OS_DATABASE, OS_DATABASE_USERNAME, OS_DB_PASSWORD
BILLING_DATABASE, BILLING_DATABASE_USERNAME, BILLING_DB_PASSWORD
```

Sincronize o script e o Secret sem gerar arquivo contendo credenciais:

```bash
./scripts/render-database-bootstrap-secret.sh
```

O script usa `kubectl create ... --dry-run=client -o yaml | kubectl apply -f -`; não habilite `set -x` e não salve a saída intermediária. Em seguida, recrie e acompanhe o Job:

```bash
kubectl -n oficina delete job database-bootstrap --ignore-not-found
kubectl apply -f k8s/database-bootstrap-job.yaml
kubectl -n oficina wait --for=condition=complete job/database-bootstrap --timeout=180s
kubectl -n oficina logs job/database-bootstrap
```

O SQL é idempotente: cria roles e bancos quando ausentes e atualiza as senhas das roles quando já existem. Assim, uma renovação de secrets pode repetir o procedimento com segurança. O Job recebe `ttlSecondsAfterFinished`; para limpeza imediata, use `kubectl -n oficina delete job database-bootstrap`. Depois do bootstrap, execute os Jobs Alembic do OS Service e do Billing Service, cada um com sua própria credencial.

## Outputs e conexão da aplicação

Após o apply, `rds_endpoint`, `rds_port`, `database_name` e `database_username` descrevem a conexão administradora. O bootstrap executado dentro do EKS cria `os_service_db`/`os_service_user` e `billing_service_db`/`billing_service_user`. As migrations Alembic pertencem aos repositórios OS e Billing e executam depois do bootstrap, usando somente a credencial de cada serviço.
