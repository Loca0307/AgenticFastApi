terraform {
  required_version = ">= 1.5.0"

  required_providers {
    archive = {
      source  = "hashicorp/archive"
      version = "~> 2.4"
    }
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    null = {
      source  = "hashicorp/null"
      version = "~> 3.2"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

variable "aws_region" {
  description = "AWS region where the Lambda function will be created."
  type        = string
  default     = "eu-south-1"
}

variable "function_name" {
  description = "Name of the Lambda function."
  type        = string
  default     = "AgenticFastapiTerraform"
}

variable "openai_api_key" {
  description = "OpenAI API key used by the Lambda function."
  type        = string
  sensitive   = true
}

variable "openai_model" {
  description = "OpenAI model used by the Lambda function."
  type        = string
  default     = "gpt-5.4-mini"
}

variable "dynamodb_table_name" {
  description = "DynamoDB table used by the FastAPI items API."
  type        = string
  default     = "FastApiDb"
}

locals {
  app_source_files = sort(tolist(setunion(
    fileset(path.module, "*.py"),
    fileset(path.module, "routes/*.py")
  )))

  app_source_hash = sha256(join("", [
    for file in local.app_source_files : filesha256("${path.module}/${file}")
  ]))
}

// Creates the package folder to be zipped for the lambda function
resource "null_resource" "package" {
  // Recreates the package when these hashes (so the files themselves) mutate
  triggers = {
    app_hash                = local.app_source_hash
    package_command_version = "3"
    requirements_hash       = filesha256("${path.module}/requirements.txt")
  }


  provisioner "local-exec" {
    working_dir = path.module
    // Command run in local to zip the project
    command = <<-EOT
      rm -rf build
      mkdir -p build/package
      python3 -m pip install --platform manylinux2014_x86_64 --implementation cp --python-version 3.11 --only-binary=:all: --upgrade -r requirements.txt -t build/package
      cp *.py build/package/
      cp -R routes build/package/routes
    EOT
  }
}


// Compresses the package folder to create the zip for the lambda function
data "archive_file" "lambda_zip" {
  type        = "zip"
  source_dir  = "${path.module}/build/package"
  output_path = "${path.module}/build/fastapi_lambda.zip"

  depends_on = [null_resource.package]
}

// Defines the IAM role of the lambda function
resource "aws_iam_role" "lambda_role" {
  name = "${var.function_name}-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      }
    ]
  })
}


// Creates the iam role to attach to the lambda function arn
resource "aws_iam_role_policy_attachment" "lambda_logs" {
  role       = aws_iam_role.lambda_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_iam_role_policy" "lambda_dynamodb" {
  name = "${var.function_name}-dynamodb"
  role = aws_iam_role.lambda_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = [
          "dynamodb:DeleteItem",
          "dynamodb:DescribeTable",
          "dynamodb:GetItem",
          "dynamodb:PutItem",
          "dynamodb:Scan",
          "dynamodb:UpdateItem",
        ]
        Effect = "Allow"
        Resource = [
          "arn:aws:dynamodb:${var.aws_region}:*:table/${var.dynamodb_table_name}",
          "arn:aws:dynamodb:${var.aws_region}:*:table/${var.dynamodb_table_name}/index/*",
        ]
      }
    ]
  })
}

// Lambda function configuration, this command actually 
// creates the lambda function instance
resource "aws_lambda_function" "fastapi" {
  architectures    = ["x86_64"]
  function_name    = var.function_name
  role             = aws_iam_role.lambda_role.arn
  handler          = "main.handler"
  runtime          = "python3.11"
  filename         = data.archive_file.lambda_zip.output_path
  source_code_hash = data.archive_file.lambda_zip.output_base64sha256
  timeout          = 15

  environment {
    variables = {
      APP_ENV        = "production"
      DYNAMODB_TABLE = var.dynamodb_table_name
      OPENAI_API_KEY = var.openai_api_key
      OPENAI_MODEL   = var.openai_model
    }
  }

  depends_on = [
    aws_iam_role_policy.lambda_dynamodb,
    aws_iam_role_policy_attachment.lambda_logs,
  ]
}


// Creates pubblic HTTP url for the function
resource "aws_lambda_function_url" "fastapi" {
  function_name      = aws_lambda_function.fastapi.function_name
  authorization_type = "NONE"
}

// Defines permission for the url to be accessed using "InvokeFunctionUrl" lambda action
// so enables users to call the url
resource "aws_lambda_permission" "allow_public_function_url" {
  statement_id           = "AllowPublicFunctionUrl"
  action                 = "lambda:InvokeFunctionUrl"
  function_name          = aws_lambda_function.fastapi.function_name
  principal              = "*"
  function_url_auth_type = "NONE"
}

// Defines permission for the url to actually be able to call the lambda function
resource "aws_lambda_permission" "allow_public_invoke_from_function_url" {
  statement_id  = "AllowPublicInvokeFromFunctionUrl"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.fastapi.function_name
  principal     = "*"
}

// terminal output of execution, prints the url to access the function
output "fastapi_url" {
  description = "Public URL for the FastAPI Lambda function."
  value       = aws_lambda_function_url.fastapi.function_url
}
